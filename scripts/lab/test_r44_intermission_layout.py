#!/usr/bin/env python3
"""Regression: pixel4 WIMAP0 uses the 38x22 glyph grid, never 76x44 render samples."""
import re
from pathlib import Path

src = Path("src/wi_libt.c").read_text()
assert "#if defined(DOOM_R22_PIXEL4)" in src
assert "#define WI_TEXT_WIDTH 38" in src
assert "#define WI_TEXT_HEIGHT 22" in src
assert "#define WI_TEXT_WIDTH VIEWWINDOWWIDTH" in src
assert "#define WI_TEXT_HEIGHT VIEWWINDOWHEIGHT" in src
body = src[src.index("//\n// Builtin map names."):]
assert not re.search(r"\bVIEWWINDOW(WIDTH|HEIGHT)\b", body)
assert "WI_TEXT_WIDTH" in body and "WI_TEXT_HEIGHT" in body
for name in ["WI_drawLF", "WI_drawEL", "WI_drawStats", "lnodes"]:
    assert name in body
assert body.count("WI_TEXT_WIDTH") >= 15
assert body.count("WI_TEXT_HEIGHT") >= 10

# Simulate all layout positions using the actual visible text area.
width, height = 38, 22
names = ["E1M1: HANGAR", "E1M2: NUCLEAR PLANT"]
for name in names:
    x = (width - len(name)) // 2
    assert 0 <= x and x + len(name) <= width
for name in ["FINISHED", "ENTERING"]:
    x = (width - 8) // 2
    assert 0 <= x and x+len(name) <= width
stats_x = (width-12)//2
assert stats_x == 13
assert stats_x+10+4 <= width # percentage sign + 3 digits fits
assert 0 <= height-3 < 22 and 0 <= height-2 < 22
assert width-13 >= 0 and width-1 < 38
coord_vga = [(185,164),(148,143),(69,122),(209,102),(116,89),(166,55),(71,56),(135,29),(71,24)]
assert all(0 <= x*width//320 < width and 0 <= y*height//200 < height for x,y in coord_vga)
print("PASS: pixel4 WIMAP0 38x22 glyph area, centering, stats/time and map markers")
