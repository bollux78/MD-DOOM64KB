#!/usr/bin/env python3
"""R51 proof-of-concept: compile Doom first-person PISG patch frames into
hardware Mega Drive sprite 8x8 patterns in ROM.

No PCX assets, external converters or additional work-RAM framebuffer.
The source WAD is the same episode-converted doom64.wad used by the ROM.
Sprite pixels are 1:1-ish *physical* pixels, independent of 76x44 world.
"""
from __future__ import annotations
from pathlib import Path
import collections
import json
import math
import os
import runpy
import struct
import sys

ROOT=Path(__file__).resolve().parents[2]
WAD=ROOT/"scripts/doom64.wad"
TARGET=ROOT/"src/r51_weapon_assets.h"
REPORT=ROOT/"src/r51_weapon_report.json"
SOURCES=runpy.run_path(str(ROOT/"scripts/genpal.py"))
raw=SOURCES["load_playpal"]()
palettes=[SOURCES["decode_subpal"](raw,s) for s in range(14)]
to_word=SOURCES["gen_color"]
to_rgb=SOURCES["gen_to_rgb"]

# Green/cyan flecks observed in hardware gun on R51. Rather than
# invent a new palette without a source-image histogram, A/B test a
# perceptual neutral-preservation penalty, only for actual PISG pixels.
# No scene PAL0/PAL1 or weapon transparency changes.
NEUTRAL=os.environ.get("DOOM_R51_WEAPON_NEUTRAL")=="1"
def dist(a,b):
    d=sum((a[i]-b[i])**2 for i in range(3))
    if not NEUTRAL:
        return d
    src_sat=max(a)-min(a)
    dst_sat=max(b)-min(b)
    if src_sat<42:
        excess=max(0,dst_sat-src_sat-12)
        d+=5*excess*excess
    green_excess=max(0,b[1]-max(b[0],b[2])-16)
    if green_excess and a[1]<=max(a[0],a[2])+16:
        d+=6*green_excess*green_excess
    return d

def wad_directory(data):
    if data[:4]!=b"IWAD":
        raise ValueError("Expected project IWAD big-endian format")
    count=struct.unpack_from(">h",data,4)[0]
    directory=struct.unpack_from(">I",data,8)[0]
    if not 0<count<4096 or directory<12 or directory+count*16>len(data):
        raise ValueError("Malformed WAD directory")
    entries=[]
    for idx in range(count):
        pos=directory+idx*16
        offset=struct.unpack_from(">I",data,pos)[0]
        size=struct.unpack_from(">H",data,pos+4)[0]
        name=data[pos+8:pos+16].split(b"\0",1)[0].decode("ascii")
        if offset+size>len(data):raise ValueError((idx,name,offset,size))
        entries.append((idx,name,data[offset:offset+size]))
    return entries

def decode_patch(patch,name):
    if len(patch)<16:raise ValueError(f"{name}: truncated patch")
    width,height,left,top=struct.unpack_from(">hhhh",patch,0)
    if not 0<width<=320 or not 0<height<=240:
        raise ValueError(f"{name}: wrong patch shape {width}x{height}")
    if 8+width*4>len(patch):raise ValueError(f"{name}: truncated columns")
    coloff=struct.unpack_from(">"+str(width)+"I",patch,8)
    pixels=[[-1]*width for _ in range(height)]
    for x,start in enumerate(coloff):
        if start>=len(patch):raise ValueError(f"{name}: bad column offset {start}")
        pos=start
        seen=0
        while pos<len(patch) and patch[pos]!=255:
            if pos+4>len(patch):raise ValueError(f"{name}: truncated post")
            y0=patch[pos];length=patch[pos+1]
            if pos+length+4>len(patch):raise ValueError(f"{name}: invalid post length")
            for dy in range(length):
                if y0+dy<height:pixels[y0+dy][x]=patch[pos+3+dy]
            pos+=length+4
            seen+=1
            if seen>height+8:raise ValueError(f"{name}: looping post")
        if pos>=len(patch):raise ValueError(f"{name}: missing sentinel")
    return dict(name=name,width=width,height=height,left=left,top=top,pixels=pixels)

entries=wad_directory(WAD.read_bytes())
frames=[]
for idx,name,patch in entries:
    # Pilot: gun/hand of the pistol (including distinct firing/recoil frames).
    if len(name)>=6 and name[:4]=="PISG" and name[4].isalpha() and name[5]=="0":
        try:
            frames.append(decode_patch(patch,name))
        except ValueError as exc:
            raise SystemExit(str(exc))
frames.sort(key=lambda f:f["name"])
if not frames:raise SystemExit("No PISG pistol patches in game WAD")
if len(frames)>24:raise SystemExit("Unusually many PISG frames; inspect WAD")

# Palette2 uses 15 opaque indices. Choose representatives based on actual
# weapon-pixel frequency, not uniform frequency of all 256 PLAYPAL colors.
hist=collections.Counter()
for f in frames:
    for row in f["pixels"]:
        hist.update(ci for ci in row if ci>=0)
sampled=sum(hist.values())
if not sampled:raise SystemExit("PISG weapon artwork is fully transparent")
candidates={}
for ci,count in hist.items():
    w=to_word(palettes[0][ci])
    if w:
        if w not in candidates:candidates[w]=[0,ci]
        candidates[w][0]+=count
# Near-black opaque entry: index0 in hardware sprites is transparent.
nearblack=to_word((0,0,36)) or 2
if nearblack not in candidates:candidates[nearblack]=[0,0]
pool=list(candidates)
if len(pool)<15:
    for ci in range(256):
        w=to_word(palettes[0][ci])
        if w and w not in candidates:
            candidates[w]=[0,ci];pool.append(w)
        if len(pool)>=15:break
if len(pool)<15:raise SystemExit("Fewer than 15 hardware colors available")
rgb={w:to_rgb(w) for w in pool}
# Start with near-black; select 14 colors by minimizing the weighted total
# squared error of actual pistol pixels in Doom PLAYPAL.
chosen=[nearblack]
for _ in range(14):
    best_choice=None
    best_gain=-1
    for w in pool:
        if w in chosen:continue
        total=0
        for ci,n in hist.items():
            target=palettes[0][ci]
            old=min(dist(target,rgb[c]) for c in chosen)
            total+=n*max(0,old-dist(target,rgb[w]))
        if total>best_gain:
            best_gain=total;best_choice=w
    if best_choice is None:raise SystemExit("Weapon color selection exhausted")
    chosen.append(best_choice)
assert len(set(chosen))==15 and 0 not in chosen
src_indices=[candidates[w][1] for w in chosen]
palette_by_sub=[[0]+[to_word(palettes[s][ci]) for ci in src_indices] for s in range(14)]
# Preserve opaque dark nearblack color under all subpalettes.
for row in palette_by_sub:row[1]=nearblack

# Palette lookup table for source palette indices; transparency handled before.
closest=[1+min(range(15),key=lambda k:dist(palettes[0][ci],to_rgb(chosen[k]))) for ci in range(256)]
records=[]
for f in frames:
    sw,sh=f["width"],f["height"]
    # Original R_DrawPSprite scales x by 76/320 logical *4 physical;
    # y by (44*5/4)/200 logical *4 physical.
    width=max(1,(sw*304+160)//320)
    height=max(1,(sh*220+100)//200)
    columns=(width+7)//8
    rows=(height+7)//8
    total=columns*rows
    if total>240:
        # Pistol pilot must not overlap the Pair-V patterns at tile index256.
        raise SystemExit(f"{f['name']} needs {total} patterns; cap is 240")
    blockx=(columns+3)//4
    blocky=(rows+3)//4
    source=f["pixels"]
    output=[]
    for y in range(height):
        sy=min(sh-1,((2*y+1)*sh)//(2*height))
        row=[]
        for x in range(width):
            sx=min(sw-1,((2*x+1)*sw)//(2*width))
            ci=source[sy][sx]
            row.append(0 if ci<0 else closest[ci])
        output.append(row)
    words=[]
    blocks=[]
    for by in range(blocky):
        for bx in range(blockx):
            bw=min(4,columns-bx*4)
            bh=min(4,rows-by*4)
            offset=len(words)//8
            # Sprite engine pattern order is column-major within a VDP sprite.
            for tx in range(bw):
                for ty in range(bh):
                    for iy in range(8):
                        yy=(by*4+ty)*8+iy
                        value=0
                        for ix in range(8):
                            xx=(bx*4+tx)*8+ix
                            pixel=output[yy][xx] if yy<height and xx<width else 0
                            value=(value<<4)|pixel
                        words.append(value)
            blocks.append((bx*32,by*32,bw,bh,offset))
    assert len(words)==total*8
    records.append(dict(name=f["name"],w=width,h=height,
                        sw=sw,sh=sh,cols=columns,rows=rows,
                        count=total,blocks=blocks,words=words))
def fmt(vals,per=8):
    return ",\n".join("    "+",".join(str(x) for x in vals[i:i+per]) for i in range(0,len(vals),per))
header=[
    "/* Generated by gen_r51_hw_weapon.py from the playable Doom WAD.",
    " * R51 experimental pistol/hand sprite tiles. GPL-2.0-or-later. */",
    "#ifndef R51_WEAPON_ASSETS_H",
    "#define R51_WEAPON_ASSETS_H",
    "#include <stdint.h>",
    "#define R51_PISTOL_TILE_BASE 16u",
    "#define R51_PISTOL_TILE_LIMIT 256u",
    "typedef struct { int16_t x,y; uint8_t w,h; uint16_t tile_offset; } R51WeaponBlock;",
    "typedef struct {",
    "  const char *name;",
    "  uint16_t pixels_w,pixels_h,tile_count;",
    "  const uint32_t *patterns;",
    "  const R51WeaponBlock *blocks;",
    "  uint8_t block_count;",
    "} R51WeaponAsset;",
    "static const uint16_t r51_weapon_pal2[14][16]={",
]
for row in palette_by_sub:
    header.append(" {"+",".join(str(x) for x in row)+"},")
header.append("};")
for n,f in enumerate(records):
    header.append(f"static const uint32_t r51_weapon_patterns_{n}[{len(f['words'])}]={{")
    header.append(fmt([f"0x{v:08X}u" for v in f["words"]],6))
    header.append("};")
    header.append(f"static const R51WeaponBlock r51_weapon_blocks_{n}[{len(f['blocks'])}]={{")
    for x,y,w,h,off in f["blocks"]:
        header.append(f" {{{x},{y},{w},{h},{off}}},")
    header.append("};")
header.append(f"static const R51WeaponAsset r51_weapon_assets[{len(records)}]={{")
for n,f in enumerate(records):
    header.append(f' {{"{f["name"]}",{f["w"]},{f["h"]},{f["count"]},'
                  f'r51_weapon_patterns_{n},r51_weapon_blocks_{n},{len(f["blocks"])}u}},')
header.append("};")
header.append(f"#define R51_WEAPON_ASSET_COUNT {len(records)}u")
header.append("#endif")
TARGET.write_text("\n".join(header)+"\n")
report=dict(source=str(WAD.relative_to(ROOT)),palette_objective="neutral-protected" if NEUTRAL else "original-rgb",frames=[
    {k:v for k,v in f.items() if k not in ("words","blocks")} |
    {"blocks":f["blocks"]} for f in records],tile_base=16,tile_limit=256,
    pixel_histogram_total=sampled,palette2_cram=palette_by_sub[0],
    palette2_distinct=len(set(palette_by_sub[0][1:])),
    hidden_if_flash_active=True,original_other_weapons_unchanged=True)
REPORT.write_text(json.dumps(report,indent=2)+"\n")
print("R51 hardware sprite pistol art generated:",json.dumps({
    "frames":[{"name":f["name"],"px":f["w"],"py":f["h"],
               "tiles":f["count"],"sprites":len(f["blocks"])} for f in records],
    "pistol_palette2_unique":report["palette2_distinct"]}))
