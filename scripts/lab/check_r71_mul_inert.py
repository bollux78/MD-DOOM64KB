#!/usr/bin/env python3
"""Check that R71-MUL code is *completely inert* with flag off, vs approved R66 source.
No run on existing HUD branch. Usage: check_r71_mul_inert.py R66_DIR R71_CHECKOUT
"""
from pathlib import Path
import sys,difflib
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_r70_inert import resolve,norm
base,branch=[Path(p) for p in sys.argv[1:3]]
p="src/r_draw.c"
s=(branch/p).read_text()
start=s.index("#if defined(DOOM_R71_MUL_ASM) && defined(__m68k__)")
marker="    int16_t hi = (int16_t)(((int32_t)a * (int16_t)b) >> 16);"
stop=s.index("#endif",start)+len("#endif")
block=s[start:stop]
assert block.count(marker)==1 and block.count('muls.w %1,%0')==1
s=s[:start]+marker+s[stop:]
orig=norm((base/p).read_text());updated=norm(resolve(s))
if orig!=updated:
    print("FAIL: source differs with R70 and MUL flags disabled")
    print("\n".join(list(difflib.unified_diff(orig,updated,lineterm=""))[:50]))
    sys.exit(1)
print("PASS R71-MUL inert: src/r_draw.c identical to R66 when flags disabled")
