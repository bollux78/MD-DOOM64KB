#!/usr/bin/env python3
"""R16 CRT HUD safety preflight. Source-level checks; not a pixel-perfect emulator."""
from pathlib import Path

video = Path("src/i_genesisv.c").read_text()
render = Path("src/r_draw.c").read_text()
build = Path("scripts/build_silent.fish").read_text()

assert "#define VDP_DISPLAY_ROWS 28" in video
assert "#if VIEWWINDOWHEIGHT != 22" in video
assert "#if VIEWWINDOWHEIGHT != 24" in video
assert "const int16_t hud_values_row = VIEWWINDOWHEIGHT + 1;" in video
assert "const int16_t hud_title_row = VIEWWINDOWHEIGHT + 3;" in video
assert "for (int16_t y = VIEWWINDOWHEIGHT; y < VDP_DISPLAY_ROWS; y++)" in video
assert "changed ? VDP_DISPLAY_ROWS : VIEWWINDOWHEIGHT" in video
assert "DOOM_R16_HUD_UP2" in build
assert "string replace -- '-DVIEWWINDOWHEIGHT=24' '-DVIEWWINDOWHEIGHT=22'" in build
assert "DOOM_R16_WEAPON_LIFT" in render
assert "vis->texturemid += DOOM_R16_WEAPON_LIFT" in render
assert "PSPRITEYSCALE = FRACUNIT * (VIEWWINDOWHEIGHT * 5 / 4)" in render
assert "DOOM_R15_SETUPMUL" in render
assert "DOOM_R13_MUL_DECOMP" not in render
assert "DOOM_R14_CLIPSCAN" not in render

# With 28 physical rows, R15 draws 24 + HUD at 25/27.
# R16 draws 22 + HUD at 23/25 and black rows 26/27.
for height, health, title, black_rows in [(24,25,27,()),(22,23,25,(26,27))]:
    assert height + 1 == health
    assert height + 3 == title
    assert height + 3 < 28
    assert all(row > title and row < 28 for row in black_rows)
    print(f"PASS: viewport={height}, HUD values={health}, title={title}, black={black_rows}")
print("PASS: R16 source preflight, R15 setupu preserved, R13/R14 absent")
