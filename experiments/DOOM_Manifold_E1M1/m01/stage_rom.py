#!/usr/bin/env python3
"""Stage a disposable Manifold candidate with an E1M1 portal_map.

NOT an acceptance claim. Runs after source audit and emission gate; only
writes to --out directory. The R128/Sega CD build tree is never modified.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil
from bootstrap import UPSTREAM, PIN
from convert_wad import read_map
from emit_portal_map import candidate, emit, nodes_from_wad

def point_inside(poly,p):
    # Convex point-in-polygon, accommodating either winding.
    signs=[]
    for i,(x,y) in enumerate(poly):
        nx,ny=poly[(i+1)%len(poly)]
        z=(nx-x)*(p[1]-y)-(ny-y)*(p[0]-x)
        if abs(z)>1:
            signs.append(z>0)
    return not signs or all(v==signs[0] for v in signs)

def stage_missing_resources(out):
    """Generate neutral 4bpp indexed PNGs and reuse valid public sample WAVs.

    Upstream's .res manifest references files absent from its own repository.
    Generated assets exist only inside the disposable working directory.
    """
    import struct
    import zlib
    def png(path,w,h):
        # PNG indexed (palette size=16), palette slot 0 transparent/black.
        def chunk(typ,payload):
            body=typ+payload
            return struct.pack(">I",len(payload))+body+struct.pack(">I",zlib.crc32(body)&0xffffffff)
        ihdr=struct.pack(">IIBBBBB",w,h,8,3,0,0,0)
        pal=bytes(i*12 for i in range(16) for _ in range(3))
        pixels=bytearray()
        for y in range(h):
            pixels.append(0)
            pixels.extend(1+((x//8+y//8)%3) for x in range(w))
        data=(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",ihdr)
              +chunk(b"PLTE",pal)+chunk(b"IDAT",zlib.compress(bytes(pixels)))
              +chunk(b"IEND",b""))
        path.write_bytes(data)
    required={
        "images/green_key_inv.png":(32,32),
        "images/red_key_inv.png":(32,32),
        "images/pause_checker.png":(16,16),
        "images/SHOTGUN_RELOAD.png":(64,128),
        "images/SMILE.png":(16,16),
        "images/FROWN.png":(16,16),
    }
    for file,(w,h) in required.items():
        dest=out/"res"/file
        if not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            png(dest,w,h)
    sample=out/"res/sfx/select.wav"
    if not sample.exists():
        raise ValueError("Upstream valid WAV sample is missing")
    for file in ["shotgun.wav","jump1.wav","jump2.wav",
                 "liftgoup.wav","enemya_wake.wav"]:
        dest=out/"res/sfx"/file
        if not dest.exists():
            shutil.copyfile(sample,dest)

def normalize_legacy_asm(out):
    """Legacy Manifold 68k .s uses '|' trailing comments rejected by our GAS.

    Strip comments on the two authored .s files; never modify SGDK or the
    original upstream checkout. Validate source still contains instructions.
    """
    for path in (out/"src").rglob("*.s"):
        filename=str(path.relative_to(out/"src"))
        source=path.read_text()
        filtered="\n".join(line.split("|",1)[0].rstrip()
                              for line in source.splitlines())+"\n"
        if not filtered.strip() or len(filtered)>len(source):
            raise ValueError(f"unexpected ASM comment conversion: {filename}")
        path.write_text(filtered)

def namespace_legacy_allocators(out):
    """Avoid collision between upstream two-argument malloc/free and SGDK macros."""
    import re
    for p in (out/"src").rglob("*"):
        if p.is_file() and p.suffix in (".c",".h"):
            source=p.read_text()
            changed=re.sub(r"\b(malloc|free)(\s*\()",lambda m:"man_"+m.group(1)+m.group(2),source)
            if changed!=source:
                p.write_text(changed)

def normalize_legacy_s16_bounds(out):
    """Resolve legacy Manifold s16 extrema absent in installed SGDK headers.

    Patch only the disposable renderer source, without changing its algorithm.
    Fail closed if upstream stops using the expected expressions.
    """
    p=out/"src/bunch_render.c"
    source=p.read_text()
    if "MAX_S16" not in source or "MIN_S16" not in source:
        raise ValueError("legacy s16 bounds not found in expected renderer")
    p.write_text(source.replace("MAX_S16","32767").replace("MIN_S16","(-32768)"))

def stage(src, wad, out):
    out=out.resolve()
    if out.exists():
        raise ValueError("destination already exists: "+str(out))
    shutil.copytree(src,out,ignore=shutil.ignore_patterns(".git","out","__pycache__"))
    stage_missing_resources(out)
    normalize_legacy_asm(out)
    namespace_legacy_allocators(out)
    normalize_legacy_s16_bounds(out)
    # Use SGDK standard Sega boot/header instead of upstream custom startup
    # that requires an unpublished out/rom_head.bin at assembler time.
    for file in ("sega.s","rom_head.c"):
        (out/"src/boot"/file).unlink(missing_ok=True)
    map_lumps=read_map(wad)
    cells, stats, missing=candidate(map_lumps,nodes_from_wad(wad),allow_gaps=True)
    # Prototype only: missing BSP cut edges are opaque and nontraversable.
    # Never synthesize an unsafe portal or mark this build geometry-validated.
    (out/"src/e1m1_map.c").write_text(emit(map_lumps,cells))
    # E1M1's split BSP contours have 1112 atomic walls; expand only this
    # isolated candidate's static budget, leaving upstream and R128 unchanged.
    header=out/"src/portal_map.h"
    h=header.read_text()
    old="#define MAX_WALLS        1024"
    if h.count(old)!=1:
        raise ValueError("upstream MAX_WALLS definition changed")
    header.write_text(h.replace(old,"#define MAX_WALLS        2048"))
    # Manifold's map chooser reads a fixed pointer table, not the Doom BSP.
    p=out/"src/maps.h"
    s=p.read_text()
    assert "#define MAPS_H" in s
    s=s.replace("#define MAPS_H","#define MAPS_H\n#include \"portal_map.h\"\nextern const portal_map e1m1_map;")
    p.write_text(s)
    p=out/"src/map_table.c"
    s=p.read_text()
    a=s.index("const uint32_t map_table[MAX_MAPS+2] = {")
    b=s.index("};",a)+2
    s=s[:a]+"""const uint32_t map_table[MAX_MAPS+2] = {
    0xDEADBEEF, 1, (uint32_t)&e1m1_map, 0, 0, 0, 0
};"""+s[b:]
    p.write_text(s)
    # Find the real player-1 THING; never place the camera at arbitrary BSP 0.
    spawns=[(x,y,angle) for x,y,angle,type_id,flags in map_lumps["THINGS"] if type_id==1]
    if len(spawns)!=1:
        raise ValueError(f"expected one player 1 spawn, got {len(spawns)}")
    x,y,angle=spawns[0]
    sp=[c["id"] for c in cells if point_inside([w["a"] for w in c["walls"]],(x*16,y*16))]
    if len(sp)!=1:
        raise ValueError(f"player spawn {x,y} falls in {len(sp)} BSP cells: {sp}")
    spawn_cell=sp[0]
    p=out/"src/level.c"
    s=p.read_text()
    expected="    const int init_player_sector = 0;"
    assert s.count(expected)==1,"Manifold player initializer changed"
    # No unconditional renderer refactor; set spawn only in this experiment.
    s=s.replace(expected,f"    const int init_player_sector = {spawn_cell};")
    old="    cur_player_pos.x = sector_0_center.x;\n    cur_player_pos.y = sector_0_center.y;"
    assert s.count(old)==1
    s=s.replace(old,f"    cur_player_pos.x = intToFix32({x});\n    cur_player_pos.y = intToFix32({y});")
    old="    cur_player_pos.ang = 0;"
    assert s.count(old)==1
    s=s.replace(old,f"    cur_player_pos.ang = {(angle*1024)//360};")
    p.write_text(s)
    report={
        "source":UPSTREAM,"pin":PIN,"map":"E1M1",
        "format":"Manifold portal_map C proof of concept",
        "player_spawn":{"x":x,"y":y,"doom_angle":angle,"manifold_cell":spawn_cell},
        "geometry":stats,"safe_for_runtime":not missing,
        "unpaired_edges_are_solid":len(missing),
        "renderer_unchanged":True,"lighting_color_placeholder":True,
        "thing_spawns_pending":True,"doors_triggers_pending":True
    }
    (out.parent/"e1m1-stage.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--wad",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    print(json.dumps(stage(args.source,args.wad,args.out),indent=2))

if __name__=="__main__":
    main()
