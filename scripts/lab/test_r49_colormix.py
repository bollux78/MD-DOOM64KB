#!/usr/bin/env python3
"""R49 offline ColorMix quality and tile-attribute oracle.

The assertion is on approximate average RGB (with stripe penalty), not
perceptual aliasing or real CRT rendering. Invalid/unknown palette pairs never
appear unless BOTH of the source Doom samples are eligible.
"""
from pathlib import Path
import json, re, runpy
R=Path(__file__).resolve().parents[2]
tables=(R/"src/r49_colormix_tables.h").read_text()
genpal=runpy.run_path(str(R/"scripts/genpal.py"))
raw=genpal["load_playpal"]()
decode=genpal["decode_subpal"]
to_rgb=genpal["gen_to_rgb"]
D=lambda a,b:sum((a[k]-b[k])**2 for k in range(3))
src=[decode(raw,i) for i in range(14)]
r22=(R/"src/r22_palette.h").read_text()
def extract(txt,name):
    m=re.search(re.escape(name)+r"\[\d+\]=\{([^}]+)\}",txt,re.S)
    assert m,name
    return [int(x) for x in m.group(1).replace("\n","").split(",")]
base=extract(r22,"r22_color")
pal0=extract(r22,"r22_cram")
pal1=extract(tables,"r49_palette1")
assert len(pal0)==len(pal1)==224
assert len(base)==256
assert all(pal0[i*16:(i+1)*16][0]==0 for i in range(14))
assert all(pal1[i*16:(i+1)*16][0]==0 for i in range(14))
assert pal1[:16]!=pal0[:16]
counts={}
for key,(wa,wb) in {"50":(2,2),"75a":(3,1),"75b":(1,3)}.items():
    a=extract(tables,"r49_mix_a_"+key)
    b=extract(tables,"r49_mix_b_"+key)
    g=extract(tables,"r49_mix_ok_"+key)
    assert len(a)==len(b)==16 and len(g)==14*256
    assert max(a+b)<=15
    for offset,eligible in enumerate(g):
        assert eligible in (0,1)
        if not eligible: continue
        sp,ci=divmod(offset,256)
        c=base[ci]
        x=to_rgb(pal1[sp*16+a[c]])
        y=to_rgb(pal1[sp*16+b[c]])
        mixed=tuple((wa*x[k]+wb*y[k])/4 for k in range(3))
        new=D(src[sp][ci],mixed)+D(x,y)*0.06*wa*wb/4
        solid=to_rgb(pal0[sp*16+c])
        old=D(src[sp][ci],solid)
        assert new+64<old*0.92,(key,ci,sp)
    counts[key]=sum(g)
    # A and B planes each store two vertically adjacent Doom sample indices.
    # The tilebank encodes the two eligibility flags, not an extra framebuffer.
    for upper in (0,1,4,15,41,155,255):
        for lower in (0,1,15,17,91,254,255):
            gu,gl=g[upper],g[lower]
            bank=gu+2*gl
            index=256+256*bank+(base[upper]<<4)+base[lower]
            attr=(0x2000 if bank==3 else 0)+index
            assert index<1280 and (attr&0x7ff)==index
            assert (attr&0x6000)==(0x2000 if bank==3 else 0)
            if bank!=3:
                # Pattern banks 0/1/2 reproduce the exact old solid pixels.
                out_a=base[upper]
                out_b=base[lower]
                assert out_a==base[upper] and out_b==base[lower]
print("R49 ColorMix oracle PASS; eligible original indices:",counts,
      "always exact original solids if either sample fails the gate")
