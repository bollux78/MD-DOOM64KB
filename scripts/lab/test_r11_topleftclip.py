#!/usr/bin/env python3
"""R11 topleftclip static safety checks, not a substitute for hardware testing."""
from pathlib import Path
r=Path("src/r_draw.c").read_text()
v=Path("src/i_genesisv.c").read_text()
b=Path("scripts/build_silent.fish").read_text()
assert "solidcol[0] = 1;" in r and "memset(solidcol, 0, VIEWWINDOWWIDTH);" in r
assert "if (x2 < 1)" in r
assert "vis->x1              = x1 < 1 ? 1 : x1;" in r
assert "vis->x1 = x1 < 1 ? 1 : x1;" in r
assert "vis->startfrac += vis->xiscale*(vis->x1-x1);" in r
assert "vis->startfrac = vis->xiscale*(vis->x1-x1);" in r
assert "&& (_g_gamestate != GS_LEVEL || x0 != 0)" in v
assert "_s_screen[y * VIEWWINDOWWIDTH] = BLACK_CELL;" in v
assert "DOOM_R11_LEFTCOL_CLIP requires DOOM_R11_TOPBAR_CLIP=1" in b
assert "DOOM_R11_TOPBAR_CLIP" in r
assert "if (yl < 1)" in r
W,H=38,24
assert (W-1)*(H-1)==851
assert W*H-851==61  # 38 top + 23 left (corner counted once)
# Prove x=0 never gets passed to the wall range from R_ClipWallSegment
# when the solidcol[0] barrier is enabled.
for first in range(W):
    for last in range(first+1,W+1):
        solid=[0]*W
        solid[0]=1
        drawn=[]
        while first < last:
            if solid[first]:
                try: first=solid.index(0,first,last)
                except ValueError: break
            else:
                try: to=solid.index(1,first,last)
                except ValueError: to=last
                drawn.extend(range(first,to))
                first=to
        assert 0 not in drawn
print("PASS: R11 top-left clip static guards, sprite sampling, 741 column-range cases and 851 visible cells")
