#!/usr/bin/env python3
"""Exact convex cells for Manifold from Doom E1M1 (M03 geometry).

Problem with the M02 cells (BSP leaf clipped to its own SEG fronts): a leaf
can extend into void wherever the solid wall that bounds it belongs to a
*different* subsector, so cells overlapped the void (walk "into nothing") and
neighbouring cells left unmatched slivers (112 unpaired edges).

M03 pipeline:
  1. planar faces from ALL linedefs (shapely node + polygonize);
  2. classify each face by sector with Doom's own BSP point lookup, rejecting
     points behind the subsector's SEGs (void);
  3. cell_i = BSP leaf_i  ∩  region(sector_i)   (convex, tiles the interior);
  4. greedily merge cells of the same Doom sector while the union stays
     convex and small (fewer portals -> shallower recursion, faster);
  5. weld to integer map units, split T-junctions, pair edges exactly.
"""
from __future__ import annotations
from collections import defaultdict
import math

from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union, polygonize
from shapely import set_precision

from bsp_cells import build

MAX_MERGED_WALLS = 16
MIN_AREA = 4.0          # map units^2, drop slivers


def point_subsector(nodes, p):
    child = len(nodes) - 1
    while not child & 0x8000:
        x, y, dx, dy = nodes[child][:4]
        side = 1 if dx * (p[1] - y) - dy * (p[0] - x) > 0 else 0   # left=1
        child = nodes[child][12 + side]
    return child & 0x7FFF


def subsector_sector(lumps, ss):
    num, first = lumps["SSECTORS"][ss]
    for seg in lumps["SEGS"][first:first + num]:
        ld = lumps["LINEDEFS"][seg[3]]
        side = ld[5 + seg[4]]
        if side != 65535:
            return lumps["SIDEDEFS"][side][5]
    raise ValueError(f"subsector {ss} without sector")


def in_front_of_segs(lumps, ss, p):
    verts = lumps["VERTEXES"]
    num, first = lumps["SSECTORS"][ss]
    for seg in lumps["SEGS"][first:first + num]:
        a, b = verts[seg[0]], verts[seg[1]]
        if (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) > 1e-6:
            return False          # left of seg = back side
    return True


def sector_regions(lumps, nodes):
    verts = lumps["VERTEXES"]
    lines = [LineString([verts[ld[0]], verts[ld[1]]]) for ld in lumps["LINEDEFS"]]
    faces = list(polygonize(unary_union(lines)))
    regions = defaultdict(list)
    void = 0
    for f in faces:
        p = f.representative_point()
        ss = point_subsector(nodes, (p.x, p.y))
        if not in_front_of_segs(lumps, ss, (p.x, p.y)):
            void += 1
            continue
        regions[subsector_sector(lumps, ss)].append(f)
    return {s: unary_union(fs) for s, fs in regions.items()}, void


def convex_ring(geom):
    """Largest polygon of geom as a clean CCW vertex list (no collinear pts)."""
    if geom.is_empty:
        return None
    polys = [g for g in getattr(geom, "geoms", [geom]) if isinstance(g, Polygon)]
    polys = [g for g in polys if g.area > MIN_AREA]
    if not polys:
        return None
    if len(polys) > 1:
        raise ValueError(f"leaf ∩ sector split into {len(polys)} pieces")
    g = polys[0].buffer(0)
    if g.interiors:
        raise ValueError("cell with hole")
    pts = list(g.exterior.coords)[:-1]
    return simplify(pts)


def simplify(pts, eps=1e-6):
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(cr) <= eps * max(1.0, math.dist(a, c)) or math.dist(a, b) < 1e-6:
                del pts[i]
                changed = True
                break
    return pts


def is_convex(poly):
    hull = poly.convex_hull
    return hull.area - poly.area <= max(1.0, 1e-4 * hull.area)


def true_cells(lumps, nodes, merge=True):
    leaves = build(lumps, nodes)
    regions, void_faces = sector_regions(lumps, nodes)
    cells = []      # (sector, shapely Polygon)
    dropped = 0
    for ss in sorted(leaves):
        leaf = Polygon(leaves[ss])
        sec = subsector_sector(lumps, ss)
        reg = regions.get(sec)
        if reg is None:
            dropped += 1
            continue
        intersection = leaf.intersection(reg)
        if __import__("os").environ.get("HERETIC_SPLIT_PIECES", "0") == "1":
            # Heretic diagnostic only: one BSP leaf may intersect disconnected
            # sector regions. Preserve *each* convex component, never choose
            # the largest and silently delete the others.
            components = [g for g in getattr(intersection, "geoms", [intersection])
                          if isinstance(g, Polygon) and g.area > MIN_AREA]
            if not components:
                dropped += 1
                continue
            for comp in components:
                ring = convex_ring(comp)
                if ring is None:
                    continue
                poly = Polygon(ring)
                if not is_convex(poly):
                    raise ValueError(f"Heretic leaf {ss} piece is non-convex; no unsafe hull")
                cells.append([sec, poly, ss])
        else:
            ring = convex_ring(intersection)
            if ring is None:
                dropped += 1
                continue
            cells.append([sec, Polygon(ring), ss])
    if merge:
        merged = True
        while merged:
            merged = False
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    if cells[i][0] != cells[j][0]:
                        continue
                    a, b = cells[i][1], cells[j][1]
                    if a.intersection(b.buffer(0.01)).length < 0.5 and \
                       a.boundary.intersection(b.boundary.buffer(0.01)).length < 1.0:
                        continue
                    u = unary_union([a, b])
                    if not isinstance(u, Polygon) or u.interiors or not is_convex(u):
                        continue
                    ring = simplify(list(u.convex_hull.exterior.coords)[:-1])
                    if len(ring) > MAX_MERGED_WALLS:
                        continue
                    cells[i][1] = Polygon(ring)
                    del cells[j]
                    merged = True
                    break
                if merged:
                    break
    stats = {"leaves": len(leaves), "void_faces": void_faces,
             "dropped_leaves": dropped, "cells": len(cells)}
    return cells, stats


def weld_and_pair(cells, lumps, clockwise=True):
    """Integer vertices, T-junction split, exact reverse-edge pairing."""
    # global weld: round to integer map units
    polys = []
    for ent in cells:
        sec, poly, ss = ent[0], ent[1], (ent[2] if len(ent) > 2 else -1)
        pts = [(round(x), round(y)) for x, y in poly.exterior.coords[:-1]]
        out = []
        for p in pts:
            if not out or out[-1] != p:
                out.append(p)
        if len(out) > 1 and out[0] == out[-1]:
            out.pop()
        area2 = sum(out[k][0] * out[(k + 1) % len(out)][1] - out[(k + 1) % len(out)][0] * out[k][1]
                    for k in range(len(out)))
        if len(out) < 3 or area2 == 0:
            continue
        if (area2 < 0) != clockwise:
            out.reverse()
        polys.append((sec, out, ss))
    allpts = set(p for _, poly, _ss in polys for p in poly)

    def on_seg(a, b, p):
        if p == a or p == b:
            return False
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if abs(dx * (p[1] - a[1]) - dy * (p[0] - a[0])) > 0.75 * L:
            return False
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (L * L)
        return 1e-9 < t < 1 - 1e-9

    split = []
    for sec, poly, ss in polys:
        pts = []
        for k, a in enumerate(poly):
            b = poly[(k + 1) % len(poly)]
            mids = [p for p in allpts if on_seg(a, b, p)]
            mids.sort(key=lambda p: (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1]))
            pts.append(a)
            pts.extend(mids)
        split.append((sec, pts, ss))
    index = {}
    for ci, (_, poly, _ss) in enumerate(split):
        for k, a in enumerate(poly):
            index.setdefault((a, poly[(k + 1) % len(poly)]), []).append(ci)
    out = []
    unpaired_internal = 0
    for ci, (sec, poly, ss) in enumerate(split):
        walls = []
        for k, a in enumerate(poly):
            b = poly[(k + 1) % len(poly)]
            nb = [c for c in index.get((b, a), []) if c != ci]
            if len(nb) > 1:
                raise ValueError(f"ambiguous edge {a}->{b}")
            walls.append({"a": a, "b": b, "neighbor": nb[0] if nb else -1})
        out.append({"id": ci, "doom_sector": sec, "ss": ss, "walls": merge_collinear(walls)})
    return out


def merge_collinear(walls):
    """Join consecutive collinear pieces with the same neighbour: each
    portal piece is recursed separately by the renderer, so T-junction
    splits towards one neighbour multiply visits for nothing."""
    def coll(w1, w2):
        a, b, c = w1["a"], w1["b"], w2["b"]
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]) == 0
    ws = list(walls)
    changed = True
    while changed and len(ws) > 3:
        changed = False
        for k in range(len(ws)):
            w1, w2 = ws[k], ws[(k+1) % len(ws)]
            if w1["neighbor"] == w2["neighbor"] and coll(w1, w2):
                ws[k] = {"a": w1["a"], "b": w2["b"], "neighbor": w1["neighbor"]}
                del ws[(k+1) % len(ws)]
                changed = True
                break
    return ws
