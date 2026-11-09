#!/usr/bin/env python3
"""DOOM E1M1 -> auditable intermediate portal cells (NOT a Manifold ROM).

Read-only IWAD parser; emits JSON with ordered BSP subsector boundaries,
Doom-sector attributes, sidedef textures and conservative adjacency.
No WAD data or copyrighted textures are committed to GitHub.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import json
from pathlib import Path
import struct

RECORDS = {
    "THINGS": "<hhhhh", "LINEDEFS": "<HHHHHHH", "SIDEDEFS": "<hh8s8s8sH",
    "VERTEXES": "<hh", "SEGS": "<HHhHHh", "SSECTORS": "<HH",
    "SECTORS": "<hh8s8sHHH",
}
REQUIRED = tuple(RECORDS)
LIMITS = {"cells": 1024, "walls": 1024, "vertices": 1024, "portals": 512}
BAD_SIDE = 0xFFFF

def unpack_records(data, fmt):
    size = struct.calcsize(fmt)
    if len(data) % size:
        raise ValueError(f"lump size {len(data)} not divisible by {size}: {fmt}")
    return [r for r in struct.iter_unpack(fmt, data)]

def name(raw):
    return raw.split(b"\0", 1)[0].decode("ascii", errors="replace").strip()

def read_map(path, map_name="E1M1"):
    data = Path(path).read_bytes()
    if len(data) < 12 or data[:4] not in (b"IWAD", b"PWAD"):
        raise ValueError("expected a DOOM IWAD/PWAD")
    n, offset = struct.unpack_from("<II", data, 4)
    if n > 100000 or offset + n * 16 > len(data):
        raise ValueError("invalid WAD directory bounds")
    directory = []
    for i in range(n):
        p, sz, raw = struct.unpack_from("<II8s", data, offset + i * 16)
        if p + sz > len(data):
            raise ValueError("lump outside WAD")
        directory.append((name(raw), data[p:p+sz]))
    starts = [i for i, (nm, _) in enumerate(directory) if nm == map_name]
    if len(starts) != 1:
        raise ValueError(f"expected exactly one {map_name} marker, got {len(starts)}")
    start = starts[0]
    nearby = dict(directory[start+1:start+12])
    missing = set(REQUIRED) - set(nearby)
    if missing:
        raise ValueError(f"missing {map_name} map lumps: {sorted(missing)}")
    return {nm: unpack_records(nearby[nm], fmt) for nm, fmt in RECORDS.items()}

def polygon_order(edges):
    """Return ordered edge indexes, or None if subsector boundary is not one closed loop."""
    if len(edges) < 3:
        return None
    by_start = defaultdict(list)
    for i, (a, b) in enumerate(edges):
        if a == b:
            return None
        by_start[a].append(i)
    for start in range(len(edges)):
        seq, seen = [], set()
        current = start
        while current not in seen:
            seen.add(current)
            seq.append(current)
            ending = edges[current][1]
            if ending == edges[start][0]:
                return seq if len(seq) == len(edges) else None
            choices = [i for i in by_start[ending] if i not in seen]
            if len(choices) != 1:
                break
            current = choices[0]
    return None

def convert(lumps, *, strict=False):
    verts = lumps["VERTEXES"]
    linedefs = lumps["LINEDEFS"]
    sides = lumps["SIDEDEFS"]
    sectors = lumps["SECTORS"]
    segs = lumps["SEGS"]
    subsectors = lumps["SSECTORS"]
    things = lumps["THINGS"]
    cells, warnings = [], []
    unmatched_twosided = 0
    edge_index = defaultdict(list)
    for cell_id, (count, first) in enumerate(subsectors):
        if first + count > len(segs):
            raise ValueError(f"subsector {cell_id} references out-of-range segs")
        indexed = list(range(first, first+count))
        edges = [(segs[i][0], segs[i][1]) for i in indexed]
        order = polygon_order(edges)
        if order is None:
            warnings.append(f"subsector {cell_id}: non-closed/multi-loop seg boundary")
            order = list(range(count))
        walls = []
        cell_sectors = set()
        for j in order:
            seg_id = indexed[j]
            v0, v1, angle, ld_idx, direction, offset = segs[seg_id]
            if v0 >= len(verts) or v1 >= len(verts) or ld_idx >= len(linedefs) or direction not in (0, 1):
                raise ValueError(f"bad vertex/linedef/side in SEG {seg_id}")
            ld = linedefs[ld_idx]
            side_idx = ld[5+direction]
            other_idx = ld[6-direction]
            if side_idx == BAD_SIDE or side_idx >= len(sides):
                raise ValueError(f"SEG {seg_id} has no valid front sidedef")
            side = sides[side_idx]
            sector_id = side[5]
            if sector_id >= len(sectors):
                raise ValueError(f"bad sector {sector_id} on SEG {seg_id}")
            cell_sectors.add(sector_id)
            wall = {
                "seg": seg_id, "linedef": ld_idx, "start": v0, "end": v1,
                "offset": offset, "direction": direction, "flags": ld[2],
                "special": ld[3], "tag": ld[4], "sector": sector_id,
                "two_sided": bool((ld[2] & 4) and other_idx != BAD_SIDE and other_idx < len(sides)),
                "texture": {"upper": name(side[2]), "lower": name(side[3]),
                            "middle": name(side[4]), "x_offset": side[0], "y_offset": side[1]},
                "neighbor": -1,
            }
            edge_index[(v0, v1)].append((cell_id, len(walls)))
            walls.append(wall)
        if len(cell_sectors) != 1:
            warnings.append(f"subsector {cell_id}: crosses Doom sectors {sorted(cell_sectors)}")
        sid = min(cell_sectors) if cell_sectors else -1
        cells.append({"id": cell_id, "doom_sector": sid, "ordered": polygon_order(edges) is not None,
                      "walls": walls})
    for cell in cells:
        for wall in cell["walls"]:
            if not wall["two_sided"]:
                continue
            matches = [(c,w) for c,w in edge_index[(wall["end"],wall["start"])] if c != cell["id"]]
            if len(matches) == 1:
                wall["neighbor"] = matches[0][0]
            else:
                unmatched_twosided += 1
                if len(matches) > 1:
                    warnings.append(f"SEG {wall['seg']}: ambiguous reverse-edge neighbors")
    active = set()
    for cell in cells:
        for wall in cell["walls"]:
            if wall["neighbor"] >= 0:
                active.add(tuple(sorted((cell["id"], wall["neighbor"]))))
    if unmatched_twosided:
        warnings.append(f"{unmatched_twosided} two-sided edges without unique reversed neighbor")
    # Connected-sector reachability is an intentionally OVERinclusive PVS
    # baseline, never an occlusion PVS. This is safe for visible geometry.
    graph = defaultdict(set)
    for a,b in active:
        graph[a].add(b)
        graph[b].add(a)
    components = []
    remaining = set(range(len(cells)))
    while remaining:
        root = min(remaining)
        seen, queue = {root}, deque([root])
        while queue:
            for next_cell in graph[queue.popleft()]:
                if next_cell not in seen:
                    seen.add(next_cell)
                    queue.append(next_cell)
        remaining -= seen
        components.append(sorted(seen))
    lim = {"cells": len(cells), "walls": sum(len(c["walls"]) for c in cells),
           "vertices": len(verts), "portals": len(active)}
    exceeded = {key: (n, LIMITS[key]) for key, n in lim.items() if n > LIMITS[key]}
    if exceeded:
        warnings.append(f"Manifold unmodified array limits exceeded: {exceeded}")
    if strict and (warnings or exceeded):
        raise ValueError("; ".join(warnings))
    world_sectors = [
        {"id": i, "floor": s[0], "ceiling": s[1], "floor_flat": name(s[2]),
         "ceiling_flat": name(s[3]), "light": s[4], "special": s[5], "tag": s[6]}
        for i, s in enumerate(sectors)
    ]
    spawn = [{"x": x, "y": y, "angle": a, "type": t, "flags": f}
             for x, y, a, t, f in things]
    return {
        "format": "doom-manifold-intermediate-v1", "limits": lim,
        "exceeds_manifold_limits": bool(exceeded),
        "warnings": warnings, "cells": cells,
        "vertices": [list(v) for v in verts], "sectors": world_sectors,
        "things": spawn, "portal_pairs": sorted(map(list, active)),
        "connected_components": components,
        "visibility_policy": "conservative-connected-components (NOT geometric PVS)",
        "playable": False,
    }

def selftest():
    assert polygon_order([(1,2),(2,3),(3,1)]) == [0,1,2]
    assert polygon_order([(2,3),(3,1),(1,2)]) is not None
    assert polygon_order([(1,2),(3,4),(4,1)]) is None
    # Synthetic rectangle split into two cells sharing a true two-sided edge.
    lumps = {key: [] for key in RECORDS}
    lumps["VERTEXES"] = [(0,0),(64,0),(64,64),(0,64),(128,0),(128,64)]
    lumps["SECTORS"] = [(0,128,b"FLAT1\0\0\0",b"CEIL1\0\0\0",160,0,0)]
    lumps["SIDEDEFS"] = [(0,0,b"-"*8,b"-"*8,b"WALL\0\0\0\0",0)]
    def line(a,b,shared=False):
        return (a,b,4 if shared else 0,0,0,0,0 if shared else BAD_SIDE)
    lumps["LINEDEFS"] = [line(0,1),line(1,2,True),line(2,3),line(3,0),
                          line(1,4),line(4,5),line(5,2)]
    # Each shared edge uses the same linedef, opposite direction.
    lumps["SEGS"] = [(0,1,0,0,0,0),(1,2,0,1,0,0),(2,3,0,2,0,0),(3,0,0,3,0,0),
                     (1,4,0,4,0,0),(4,5,0,5,0,0),(5,2,0,6,0,0),(2,1,0,1,1,0)]
    lumps["SSECTORS"] = [(4,0),(4,4)]
    result = convert(lumps, strict=True)
    assert result["portal_pairs"] == [[0,1]]
    assert result["limits"] == {"cells":2,"walls":8,"vertices":6,"portals":1}
    assert result["connected_components"] == [[0,1]]
    assert result["cells"][0]["walls"][1]["neighbor"] == 1
    assert result["cells"][1]["walls"][3]["neighbor"] == 0
    assert result["playable"] is False
    print("synthetic topology/portal test: PASS")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wad", type=Path)
    ap.add_argument("--map", default="E1M1")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.wad or not args.out:
        ap.error("--wad and --out required except for --selftest")
    result = convert(read_map(args.wad,args.map),strict=args.strict)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, separators=(",",":")) + "\n")
    print(json.dumps({"limits":result["limits"],"warnings":result["warnings"],
                      "components":len(result["connected_components"]),
                      "playable":result["playable"]},indent=2))

if __name__ == "__main__":
    main()
