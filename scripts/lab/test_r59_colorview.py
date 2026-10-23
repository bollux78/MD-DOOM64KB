#!/usr/bin/env python3
"""R59 source and generated-table contract: profile identity and hot-switch paths."""
from pathlib import Path
import hashlib, json, re
ROOT=Path(__file__).resolve().parents[2]
d=ROOT/"src"
header=(d/"r59_color_tables.h").read_text()
cm=(d/"r56_tables.h").read_text()
report=json.loads((d/"r59_color_report.json").read_text())
assert len(report["order"])==4
assert report["order"]==["CM6","Balanced","Tolerant","Accents"]
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
for short,name in (("balanced","a6-balanced"),("tolerant","a6-tolerant"),("accents","a6-accents")):
    historical=(ROOT/"dist/r59-colorview/historical"/(name+".h")).read_text()
    assert hashlib.sha256(historical.encode()).hexdigest()==report["profiles"][name]
    for field in f:
        dims1,raw1=initializer(historical,"r56_"+field)
        dims2,raw2=initializer(header,"r59_"+short+"_"+field)
        assert dims1==dims2 and raw1==raw2,(name,field)
    assert "#define R56_ANCHORS 6" in historical
assert "R59_COLOR_MODES 4" in header
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
for key in ("M_ChangeColorMode","Color mode:","CM6","Balanced","Tolerant","Accents"):
    assert key in menu,key
print("PASS R59 four ROM-resident palettes/codebooks, CM6 unchanged, all A6 byte-exact, and runtime wiring")
