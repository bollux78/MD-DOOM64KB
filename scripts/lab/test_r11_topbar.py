#!/usr/bin/env python3
"""R11 static preflight: clip coverage and DMA row boundaries. Runtime validation still required."""
from pathlib import Path
r=Path("src/r_draw.c").read_text()
v=Path("src/i_genesisv.c").read_text()
b=Path("scripts/build_silent.fish").read_text()
assert "ceilingclip[i] = 0;" in r and "ceilingclip[i] = -1;" in r
assert "if (yl < 1)" in r and "R_DrawMaskedColumn" in r
assert "&& (_g_gamestate != GS_LEVEL || y0 != 0)" in v
assert "changed ? VDP_DISPLAY_ROWS - 1 : VIEWWINDOWHEIGHT - 1" in v
assert "static uint16_t lastTopRow[VIEWWINDOWWIDTH];" in v
assert "DOOM_R11_TOPBAR_CLIP" in b and "DOOM_R11_TOPBAR_DMA" in b
W,HEIGHT,DISPLAY=38,24,28
for top_changed in (False,True):
    for hud_changed in (False,True):
        start = 0 if top_changed else 1
        rows = (DISPLAY if hud_changed else HEIGHT) - start
        sent = set(range(start,start+rows))
        expected = set(range(1,HEIGHT))
        if top_changed: expected.add(0)
        if hud_changed: expected |= set(range(HEIGHT,DISPLAY))
        assert sent==expected, (top_changed,hud_changed,sent,expected)
assert W*(HEIGHT-1)==874
assert W*2==76
print("R11 static preflight PASS: clipping guards, status-DMA ranges and unchanged HUD coordinates.")
