#!/usr/bin/env python3
"""Rebuild closed convex cells from vanilla Doom BSP partition planes.

Vanilla SSECTORS/SEGS may be OPEN because internal BSP split edges are implicit.
Do not assume their SEG vertices form a polygon. Traverse NODES from its root,
clip the map AABB on each half-plane, and attach each child subsector to a
convex polygon. Output is a geometry diagnostic, NOT a runnable portal_map.

Coordinates are carried in floating point during intersection only. Quantized
vertices are a *preview*; exact portal pairing must be audited before runtime.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import json
import math
import struct
from pathlib import Path
from convert_wad import read_map, name

NODE_FORMAT = "<12h2H"
EPS = 1e-7

def vertices_of_map(lumps):
    v = lumps["VERTEXES"]
    if not v:
        raise ValueError("map has no vertices")
    lo_x = min(x for x,y in v)-4
    hi_x = max(x for x,y in v)+4
    lo_y = min(y for x,y in v)-4
    hi_y = max(y for x,y in v)+4
    return [(lo_x,lo_y),(hi_x,lo_y),(hi_x,hi_y),(lo_x,hi_y)]

def cross(node,p):
    x,y,dx,dy = node[:4]
    return dx*(p[1]-y)-dy*(p[0]-x)

def clipped(poly,node, positive):
    if not poly:
        return []
    out = []
    previous = poly[-1]
    prev_val = cross(node,previous) * (1 if positive else -1)
    for current in poly:
        curr_val = cross(node,current) * (1 if positive else -1)
        prev_inside = prev_val >= -EPS
        curr_inside = curr_val >= -EPS
        if prev_inside != curr_inside:
            ratio = prev_val / (prev_val-curr_val)
            out.append((previous[0]+ratio*(current[0]-previous[0]),
                        previous[1]+ratio*(current[1]-previous[1])))
        if curr_inside:
            out.append(current)
        previous,prev_val=current,curr_val
    # collapse duplicate successive coordinates
    result=[]
    for p in out:
        if not result or math.dist(p,result[-1])>EPS:
            result.append(p)
    if len(result)>1 and math.dist(result[0],result[-1])<=EPS:
        result.pop()
    return result if len(result)>=3 else []

def area(poly):
    return 0.5*sum(poly[i][0]*poly[(i+1)%len(poly)][1] -
                   poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))

def build(lumps, nodes):
    if not nodes:
        raise ValueError("NODES is empty")
    root = len(nodes)-1
    cells = {}
    stack = [(root,vertices_of_map(lumps))]
    steps=0
    while stack:
        child, poly=stack.pop()
        steps+=1
        if steps>2*len(nodes)+100:
            raise ValueError("BSP cycle or invalid tree")
        if child & 0x8000:
            index=child & 0x7fff
            if index>=len(lumps["SSECTORS"]):
                raise ValueError(f"invalid BSP subsector {index}")
            if index in cells:
                raise ValueError(f"duplicate BSP leaf {index}")
            cells[index]=poly
            continue
        if child>=len(nodes):
            raise ValueError(f"invalid BSP node {child}")
        node=nodes[child]
        # DOOM BSP convention: side 0 = cross > 0, child RIGHT;
        # side 1 = cross < 0, child LEFT.
        right=clipped(poly,node,True)
        left=clipped(poly,node,False)
        stack.append((node[13],left))
        stack.append((node[12],right))
    if len(cells)!=len(lumps["SSECTORS"]):
        raise ValueError(f"BSP visits {len(cells)}/{len(lumps['SSECTORS'])} subsectors")
    return cells

def audit(lumps,nodes):
    cells=build(lumps,nodes)
    segs=lumps["SEGS"]
    missing=0
    mismatch=[]
    areas=[]
    for i, poly in sorted(cells.items()):
        count,first=lumps["SSECTORS"][i]
        areas.append(abs(area(poly)))
        if len(poly)<3 or abs(area(poly))<EPS:
            missing+=1
            continue
        for seg in segs[first:first+count]:
            # Existing seg midpoint must lie within the BSP leaf clipping
            # hull, allowing sub-unit interpolation rounding tolerances.
            a,b=seg[:2]
            va=lumps["VERTEXES"][a]
            vb=lumps["VERTEXES"][b]
            midpoint=((va[0]+vb[0])/2,(va[1]+vb[1])/2)
            # Convex polygon containment with either winding.
            tests=[]
            for j,p in enumerate(poly):
                q=poly[(j+1)%len(poly)]
                tests.append((q[0]-p[0])*(midpoint[1]-p[1])-
                             (q[1]-p[1])*(midpoint[0]-p[0]))
            if min(tests)<-0.75 and max(tests)>0.75:
                mismatch.append((i,seg[3]))
    return {"subsectors":len(cells),"closed_cells":sum(len(p)>=3 for p in cells.values()),
            "zero_area":missing,"seg_midpoint_outside":len(mismatch),
            "mismatch_examples":mismatch[:12],
            "polygon_edge_count":sum(len(p) for p in cells.values()),
            "cell_area_sum":round(sum(areas),1),
            "cell_max_edges":max(map(len,cells.values()))}

def synthetic():
    # split a rectangle in half: line x=5, positive cross points to left
    nodes=[(5,0,0,10, 10,0,0,5, 10,0,5,10, 0x8000,0x8001)]
    lumps={"VERTEXES":[(0,0),(10,0),(10,10),(0,10)],
           "SSECTORS":[(0,0),(0,0)],"SEGS":[]}
    cells=build(lumps,nodes)
    assert len(cells)==2 and len(cells[0])==4 and len(cells[1])==4
    assert abs(sum(abs(area(x)) for x in cells.values())-18*18)<1e-6
    assert max(p[0] for p in cells[0])<=5+EPS
    assert min(p[0] for p in cells[1])>=5-EPS
    print("BSP synthetic closed cells: PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--wad", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--selftest", action="store_true")
    args=ap.parse_args()
    if args.selftest:
        synthetic()
        return
    if not args.wad:
        ap.error("--wad required")
    # Read NODES using the same pinned WAD directory parser but without
    # modifying the original map's source records.
    data=args.wad.read_bytes()
    n,off=struct.unpack_from("<II",data,4)
    directory=[(name(struct.unpack_from("<II8s",data,off+i*16)[2]),
                struct.unpack_from("<II8s",data,off+i*16)[:2]) for i in range(n)]
    starts=[i for i,(nm,_) in enumerate(directory) if nm=="E1M1"]
    if len(starts)!=1:
        raise ValueError("ambiguous E1M1")
    raw={}
    for nm,(p,size) in directory[starts[0]+1:starts[0]+12]:
        if nm=="NODES":
            if size%struct.calcsize(NODE_FORMAT):
                raise ValueError("bad NODES record alignment")
            raw[nm]=list(struct.iter_unpack(NODE_FORMAT,data[p:p+size]))
    if "NODES" not in raw:
        raise ValueError("missing NODES")
    report=audit(read_map(args.wad),raw["NODES"])
    print(json.dumps(report,indent=2))
    if args.out:
        args.out.write_text(json.dumps(report,indent=2)+"\n")
    if report["zero_area"] or report["seg_midpoint_outside"]:
        raise SystemExit("BSP reconstruction geometry audit failed")

if __name__=="__main__":
    main()
