#!/usr/bin/env python3
"""Produce a *candidate* Manifold portal_map from real DOOM E1M1 BSP cells.

Fail closed when solid boundaries, adjacency or Manifold static limits cannot
be proven. This stage is intended for geometry development, not final visual
or gameplay parity. Assets/WAD remain local to the build runner.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import struct
from bsp_cells import build, clip_to_seg_front, NODE_FORMAT
from convert_wad import read_map, name

SCALE=16
MAX_CELLS=1024
MAX_WALLS=2048
MAX_VERTICES=1024
MAX_PORTALS=512

def nodes_from_wad(path):
    data=Path(path).read_bytes()
    if len(data)<12 or data[:4] not in (b"IWAD",b"PWAD"):
        raise ValueError("bad WAD")
    count,offset=struct.unpack_from("<II",data,4)
    if count>100000 or offset+count*16>len(data):
        raise ValueError("invalid directory")
    entries=[]
    for i in range(count):
        pos,size,nm=struct.unpack_from("<II8s",data,offset+i*16)
        if pos+size>len(data):
            raise ValueError("invalid lump")
        entries.append((name(nm),pos,size))
    starts=[i for i,x in enumerate(entries) if x[0]=="E1M1"]
    if len(starts)!=1:
        raise ValueError("ambiguous E1M1")
    for nm,pos,size in entries[starts[0]+1:starts[0]+12]:
        if nm=="NODES":
            if size%struct.calcsize(NODE_FORMAT):
                raise ValueError("invalid NODES size")
            return list(struct.iter_unpack(NODE_FORMAT,data[pos:pos+size]))
    raise ValueError("NODES not found")

def quantize(poly):
    out=[]
    for x,y in poly:
        p=(round(x*SCALE),round(y*SCALE))
        if not out or out[-1]!=p:
            out.append(p)
    if len(out)>1 and out[0]==out[-1]:
        out.pop()
    return out

def cross(a,b,p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])

def along(a,b,p,tol=1):
    if abs(cross(a,b,p))>tol*max(abs(b[0]-a[0]),abs(b[1]-a[1]),1):
        return False
    return min(a[0],b[0])-tol<=p[0]<=max(a[0],b[0])+tol and min(a[1],b[1])-tol<=p[1]<=max(a[1],b[1])+tol

def split_edges(polygons):
    # All BSP intersections split both faces into common atomic edges.
    all_points=set(p for poly in polygons.values() for p in poly)
    result={}
    for cell,poly in polygons.items():
        points=[]
        for i,a in enumerate(poly):
            b=poly[(i+1)%len(poly)]
            dx=b[0]-a[0];dy=b[1]-a[1]
            if not (dx or dy):
                raise ValueError("zero-length edge")
            extra=[p for p in all_points if p!=a and p!=b and along(a,b,p,0)]
            extra.sort(key=lambda p:(p[0]-a[0])*dx+(p[1]-a[1])*dy)
            points.extend([a]+extra)
        if len(points)<3:
            raise ValueError("non-polygon")
        result[cell]=points
    return result

def source_sector(lumps,cell):
    num,first=lumps["SSECTORS"][cell]
    out=set()
    for seg in lumps["SEGS"][first:first+num]:
        ld=lumps["LINEDEFS"][seg[3]]
        side_idx=ld[5+seg[4]]
        if side_idx!=65535:
            out.add(lumps["SIDEDEFS"][side_idx][5])
    if len(out)!=1:
        raise ValueError(f"cell {cell} ambiguous Doom sector {out}")
    return next(iter(out))

def source_wall(lumps,cell,a,b):
    """Find original Doom SEG lying along this boundary in the cell."""
    num,first=lumps["SSECTORS"][cell]
    verts=lumps["VERTEXES"]
    edges=[]
    for seg in lumps["SEGS"][first:first+num]:
        x=tuple(int(v)*SCALE for v in verts[seg[0]])
        y=tuple(int(v)*SCALE for v in verts[seg[1]])
        if x==y:
            continue
        # An atomic wall piece can be shorter than or overlap original SEG.
        if along(x,y,a,1) and along(x,y,b,1):
            edges.append(seg)
    if len(edges)>1:
        # Usually duplicates are geometric aliases; flag them for inspection.
        if len({e[3] for e in edges})>1:
            raise ValueError(f"ambiguous seg coverage at cell {cell}")
    return edges[0] if edges else None

def candidate(lumps,nodes,allow_gaps=False):
    import os
    if os.environ.get("MANIFOLD_CELLS","exact")=="exact":
        return exact_candidate(lumps,nodes)
    return legacy_candidate(lumps,nodes,allow_gaps)

def exact_candidate(lumps,nodes):
    import true_cells as T
    merge=__import__("os").environ.get("MANIFOLD_MERGE","1")=="1"
    raw,tstats=T.true_cells(lumps,nodes,merge=merge)
    clockwise=__import__("os").environ.get("MANIFOLD_WINDING","cw")!="ccw"
    cells=T.weld_and_pair(raw,lumps,clockwise=clockwise)
    for c in cells:
        for w in c["walls"]:
            w["a"]=(w["a"][0]*SCALE,w["a"][1]*SCALE)
            w["b"]=(w["b"][0]*SCALE,w["b"][1]*SCALE)
            w["seg"]=-1
    pairs={tuple(sorted((c["id"],w["neighbor"]))) for c in cells for w in c["walls"] if w["neighbor"]>=0}
    points={p for c in cells for w in c["walls"] for p in (w["a"],w["b"])}
    stats=dict(tstats,walls=sum(len(c["walls"]) for c in cells),vertices=len(points),
               portal_pairs=len(pairs),nonmatching_internal_edges=0,method="exact")
    for k,limit in [("cells",MAX_CELLS),("walls",MAX_WALLS),("vertices",MAX_VERTICES)]:
        if stats[k]>limit: raise ValueError(f"limit {k} {stats[k]}>{limit}")
    return cells,stats,[]

def legacy_candidate(lumps,nodes,allow_gaps=False):
    leaves=clip_to_seg_front(lumps,build(lumps,nodes))
    vanished=[i for i,p in leaves.items() if len(p)<3]
    if vanished:
        raise ValueError(f'{len(vanished)} empty cells after SEG clipping; examples {vanished[:12]}')
    polys={i:quantize(p) for i,p in leaves.items()}
    polys=split_edges(polys)
    # Manifold cells are counter-clockwise (positive signed area, like the
    # upstream test maps); its renderer culls walls by projected order, so a
    # clockwise cell draws nothing. Normalise every cell before pairing.
    def _signed_area(poly):
        return sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1]
                   for i in range(len(poly)))/2
    want_positive = __import__("os").environ.get("MANIFOLD_WINDING","cw")=="ccw"
    polys={i:(p if (_signed_area(p)>0)==want_positive else list(reversed(p))) for i,p in polys.items()}
    if len(polys)>MAX_CELLS:
        raise ValueError("too many cells")
    indices=defaultdict(list)
    for cell,poly in polys.items():
        for i,a in enumerate(poly):
            b=poly[(i+1)%len(poly)]
            indices[(a,b)].append((cell,i))
    sectors=[source_sector(lumps,i) for i in sorted(polys)]
    cells=[]
    missing=[]
    pairs=set()
    for i in sorted(polys):
        poly=polys[i]
        entries=[]
        for j,a in enumerate(poly):
            b=poly[(j+1)%len(poly)]
            candidates=[c for c,k in indices.get((b,a),[]) if c!=i]
            if len(candidates)>1:
                raise ValueError(f"ambiguous opposite edge: {i}:{j}")
            neighbor=candidates[0] if candidates else -1
            seg=source_wall(lumps,i,a,b)
            ld=lumps["LINEDEFS"][seg[3]] if seg else None
            if seg is not None and not (ld[2]&4 and ld[5]!=65535 and ld[6]!=65535):
                neighbor=-1
            if seg is None and neighbor<0:
                missing.append({"cell":i,"edge":j,"a":a,"b":b})
            if neighbor>=0:
                pairs.add(tuple(sorted((i,neighbor))))
            entries.append({"a":a,"b":b,"neighbor":neighbor,
                            "seg":seg[3] if seg else -1})
        cells.append({"id":i,"doom_sector":sectors[i],"walls":entries})
    points={p for c in cells for w in c["walls"] for p in (w["a"],w["b"])}
    wall_count=sum(len(c["walls"]) for c in cells)
    stats={"cells":len(cells),"walls":wall_count,"vertices":len(points),
           "portal_pairs":len(pairs),"nonmatching_internal_edges":len(missing)}
    exceeded={
        k:(stats[k],limit) for k,limit in [
            ("cells",MAX_CELLS),("walls",MAX_WALLS),
            ("vertices",MAX_VERTICES),("portal_pairs",MAX_PORTALS)
        ] if stats[k]>limit
    }
    if exceeded:
        raise ValueError(f"upstream Manifold static limits exceeded: {exceeded}")
    if missing and not allow_gaps:
        raise ValueError(f"{len(missing)} unpaired BSP edges; first {missing[:4]}")
    return cells,stats,missing

def as_c_array(typ,name_,values,per_line=12):
    return f"static const {typ} {name_}[{len(values)}] = {{\n"+ "".join(
        "  "+", ".join(map(str,values[i:i+per_line]))+",\n" for i in range(0,len(values),per_line))+"};\n"

# colors.h indices: 6 light steel, 12 steel, 7 yellow, 13 dark yellow, 3 light green, 9 green
HEIGHT_SCALE=2
WALL_COLOR_CYCLE=(12,6,13,7,9,3)
FLOOR_COLOR=13   # dark yellow/brown
CEIL_COLOR=12    # steel

def emit(lumps,cells):
    vertices={}
    sectors=[]
    walls=[]
    portals=[]
    quad=[]
    colors=[]
    collision_verts=[]
    for cell in cells:
        offset=len(walls)
        first_portal=len(portals)
        for w in cell["walls"]:
            p=w["a"]
            if p not in vertices:
                x,y=p
                if (x%SCALE or y%SCALE):
                    # Manifold vertex uses s16 x/y; rounding must be audited.
                    pass
                vertices[p]=len(vertices)
            walls.append(vertices[p])
            portals.append(w["neighbor"])
            collision_verts.extend([w["a"],w["b"]])
            dx=w["b"][0]-w["a"][0]
            dy=w["b"][1]-w["a"][1]
            # upstream editor/line.py normal_quadrant: angle = atan2(dx, dy)
            import math
            ang=math.degrees(math.atan2(dx,dy))%360
            quad.append(7 if ang==0 else 0 if ang<90 else 4 if ang==90 else 1 if ang<180
                        else 5 if ang==180 else 2 if ang<270 else 6 if ang==270 else 3)
            # Until valid texture resources exist, NEVER enter the texture path.
            # [texture, upper-step color, lower-step color, solid color].
            # Non-zero solid color = untextured wall in that colors.h index;
            # vary by Doom sector so rooms read apart (placeholder palette).
            wc=WALL_COLOR_CYCLE[cell["doom_sector"] % len(WALL_COLOR_CYCLE)]
            colors.extend([0,wc,wc,wc])
        # Manifold walls use a closing vertex per cell.
        walls.append(vertices[cell["walls"][0]["a"]])
        sectors.extend([offset,first_portal,len(cell["walls"]),cell["doom_sector"]])
    actual_points=list(vertices)
    sector_params=[]
    for floor,ceil,fl,ce,light,special,tag in lumps["SECTORS"]:
        light_level=max(-2,min(2,round((light-160)/40)))  # colors.c tables cover -2..2
        # 12.4 heights, doubled: Manifold projects 64x144 with a wide FOV and
        # treats openings <=60 as closed doors / steps >=40 as walls.
        floor_h=floor*16*HEIGHT_SCALE;ceil_h=ceil*16*HEIGHT_SCALE
        if not (-32768<=floor_h<=32767 and -32768<=ceil_h<=32767):
            raise ValueError("sector height exceeds Manifold 12.4 format")
        # param 0 is packed {s8 light_level; u8 ceil<<4 | floor} (sector_group.h)
        packed=((light_level & 0xFF) << 8) | (CEIL_COLOR << 4) | FLOOR_COLOR
        if packed >= 0x8000: packed -= 0x10000
        sector_params.extend([packed,0,0,0,floor_h,ceil_h,0,0])
    text="#include <genesis.h>\n#include \"portal_map.h\"\n#include \"sector_group.h\"\n"
    text+="/* GENERATED, geometry proof-of-concept; textures/colors NOT final */\n"
    text+=as_c_array("s16","e1_sectors",sectors)
    text+=as_c_array("u16","e1_walls",walls)
    text+=as_c_array("s16","e1_portals",portals)
    text+=as_c_array("u8","e1_quadrants",quad)
    text+=as_c_array("u8","e1_wall_colors",colors)
    text+=as_c_array("u8","e1_wall_repetitions",[1]*len(portals))
    text+=as_c_array("s16","e1_group_params",sector_params)
    text+=as_c_array("u8","e1_group_types",[0]*len(lumps["SECTORS"]))
    text+=as_c_array("s16","e1_group_triggers",[0]*(len(lumps["SECTORS"])*8))
    # Conservative all-cells PVS/PHS avoids NULL dereferences in sound/AI.
    # This is temporary and deliberately slow; optimize after live gameplay.
    runs=[]
    remaining=len(cells)
    while remaining:
        chunk=min(127,remaining)
        runs.append(chunk)
        remaining-=chunk
    runs.append(0)
    text+=as_c_array("s8","e1_visibility_all",runs)
    text+=as_c_array("u32","e1_visibility_offsets",[0]*len(cells))
    text+="static const vertex e1_vertices[] = {\n"
    for x,y in actual_points:
        if not (-32768<=round(x/SCALE)<=32767 and -32768<=round(y/SCALE)<=32767):
            raise ValueError("vertex outside Manifold signed 16-bit range")
        text+=f"  {{.x={round(x/SCALE)},.y={round(y/SCALE)}}},\n"
    text+="};\n"
    text+="static const vertex e1_collision_vertices[] = {\n"
    for x,y in collision_verts:
        text+=f"  {{.x={round(x/SCALE)},.y={round(y/SCALE)}}},\n"
    text+="};\n"
    text+=f"""const portal_map e1m1_map = {{
  .num_sector_groups={len(lumps["SECTORS"])},
  .num_sectors={len(cells)}, .num_walls={len(portals)},
  .num_verts={len(vertices)},
  .sectors=e1_sectors,.sector_group_types=e1_group_types,
  .sector_group_params=e1_group_params,.sector_group_triggers=e1_group_triggers,
  .walls=e1_walls,.portals=e1_portals,.wall_colors=e1_wall_colors,\n  .wall_tex_repetitions=e1_wall_repetitions,\n  .collision_vertexes=e1_collision_vertices,
  .wall_norm_quadrants=e1_quadrants,.vertexes=e1_vertices,
  .has_pvs=0,.name="E1M1 geometry experimental",\n  .sector_pvs_offsets=e1_visibility_offsets,.sector_pvs_entries=e1_visibility_all,\n  .sector_phs_offsets=e1_visibility_offsets,.sector_phs_entries=e1_visibility_all,
  .num_things=0,.things=0
}};
"""
    return text

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--wad",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    ap.add_argument("--out-c",type=Path)
    ap.add_argument("--allow-gaps",action="store_true",
                    help="diagnostic only; ghost boundaries may render incorrectly")
    args=ap.parse_args()
    lumps=read_map(args.wad)
    nodes=nodes_from_wad(args.wad)
    try:
        cells,stats,missing=candidate(lumps,nodes,allow_gaps=args.allow_gaps)
        result={"status":"CANDIDATE","stats":stats,"missing_examples":missing[:12],
                "safe_for_runtime":not missing}
        if args.out_c:
            args.out_c.write_text(emit(lumps,cells))
            result["generated_source"]=str(args.out_c)
    except ValueError as exc:
        result={"status":"BLOCKED","reason":str(exc),"safe_for_runtime":False}
    args.report.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    if not result["safe_for_runtime"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
