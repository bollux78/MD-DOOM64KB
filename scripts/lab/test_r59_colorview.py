#!/usr/bin/env python3
"""R59 source and generated-table contract: profile identity and hot-switch paths."""
from pathlib import Path
import hashlib, json, re
ROOT=Path(__file__).resolve().parents[2]
d=ROOT/"src"
header=(d/"r59_color_tables.h").read_text()
cm=(d/"r56_tables.h").read_text()
report=json.loads((d/"r59_color_report.json").read_text())
assert len(report["order"])==6
assert report["order"]==["CM6","Balanced","Tolerant","Accents","A4 Tolerant","A4 Accents"]
assert hashlib.sha256(cm.encode()).hexdigest()==report["cm6_sha256"]
f=("pal0","pal1","pairs_even","pairs_odd","wall_even","wall_odd",
   "flat_even","flat_odd","comp_even","comp_odd")
def initializer(src,name):
    pat=r"\b"+re.escape(name)+r"((?:\[\d+\])+)\s*=\s*\{"
    m=re.search(pat,src)
    assert m is not None,name
    start=m.end()-1;depth=0
    for end in range(start,len(src)):
        if src[end]=="{": depth+=1
        elif src[end]=="}":
            depth-=1
            if depth==0:
                return m.group(1),src[start:end+1]
    raise AssertionError("Unclosed initializer: "+name)
for short,name in (("balanced","a6-balanced"),("tolerant","a6-tolerant"),("accents","a6-accents"),
                   ("a4_tolerant","a4-tolerant"),("a4_accents","a4-accents")):
    historical=(ROOT/"dist/r59-colorview/historical"/(name+".h")).read_text()
    assert hashlib.sha256(historical.encode()).hexdigest()==report["profiles"][name]
    for field in f:
        dims1,raw1=initializer(historical,"r56_"+field)
        dims2,raw2=initializer(header,"r59_"+short+"_"+field)
        assert dims1==dims2 and raw1==raw2,(name,field)
    assert "#define R56_ANCHORS "+("4" if short.startswith("a4_") else "6") in historical
assert "R59_COLOR_MODES 6" in header
assert '#include "r56_tables.h"' in header
for field in f:
    assert initializer(cm,"r56_"+field)[1]
video=(d/"r22_video.inc").read_text()
menu=(d/"m_text.c").read_text()
for key in ("R59_CURRENT.comp_even","R59_CURRENT.comp_odd",
            "R59_CURRENT.wall_even","R59_CURRENT.wall_odd",
            "R59_CURRENT.flat_even","R59_CURRENT.flat_odd",
            "R59_CURRENT.pairs_even","R59_CURRENT.pairs_odd",
            "R59_CURRENT.pal0","R59_CURRENT.pal1",
            "R59_ChangeColor","VDP_setEnable(FALSE);",
            "R47_LoadPairTiles();"):
    assert key in video,key
for key in ("M_ChangeColorMode","Color mode:","CM6","Balanced","Tolerant","Accents","A4 Tolerant","A4 Accents"):
    assert key in menu,key
native=(d/"r35_native4.inc").read_text()
assert "#if defined(DOOM_R59_COLOR_VIEW)" in native
assert "PAL_setColors(0,R59_CURRENT.pal0[0],16,CPU)" in native
assert "PAL_setColors(16,R59_CURRENT.pal1[0],16,CPU)" in native
assert "r59_color_dirty=0; /* native exit rebuilt selected tiles and CRAM */" in native
assert "if(r59_color_dirty && r35_native_active<0)" in video
def nums(src,name):
    return list(map(int,re.findall(r"\d+",initializer(src,name)[1])))
mode_names=("cm6","balanced","tolerant","accents","a4_tolerant","a4_accents")
sources={name:cm if name=="cm6" else header for name in mode_names}
prefixes={name:"r56_" if name=="cm6" else "r59_"+name+"_" for name in mode_names}
for i,left in enumerate(mode_names):
    for right in mode_names[i+1:]:
        diffs={}
        for field in f:
            a=nums(sources[left],prefixes[left]+field)
            b=nums(sources[right],prefixes[right]+field)
            assert len(a)==len(b),(left,right,field,len(a),len(b))
            diffs[field]=sum(x!=y for x,y in zip(a,b))
        print("R59 profile comparison",left,"vs",right,
              "palette words",diffs["pal0"]+diffs["pal1"],
              "pair nibbles",diffs["pairs_even"]+diffs["pairs_odd"],
              "wall LUT indices",diffs["wall_even"]+diffs["wall_odd"],
              "COLORMAP indices",diffs["comp_even"]+diffs["comp_odd"],flush=True)
        assert (diffs["pairs_even"]+diffs["pairs_odd"]+
                diffs["wall_even"]+diffs["wall_odd"])>0, (
                "two selectable profiles are identical",left,right)
# A4 and A6 are DIFFERENT hardware palettes, not just remapped pair codes.
for a4 in ("a4_tolerant","a4_accents"):
    for a6 in ("balanced","tolerant","accents"):
        assert any(nums(sources[a4],prefixes[a4]+p)!=nums(sources[a6],prefixes[a6]+p) for p in ("pal0","pal1"))
assert "R59_COLOR_MODES-1u)%R59_COLOR_MODES" in video
print("PASS R59 v3 native palette restore, exact six R57/R58 modes, A4 vs A6 palette differences")
