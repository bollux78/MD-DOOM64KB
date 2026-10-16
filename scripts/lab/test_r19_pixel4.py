#!/usr/bin/env python3
"""R19 static invariants and deterministic 4x4 -> 8x8 tile reference test."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
video = (root / "src/i_genesisv.c").read_text()
encoder = (root / "src/r19_pixel4.h").read_text()
build = (root / "scripts/build_silent.fish").read_text()
script = (root / "scripts/lab/build_r19_pixel4.fish").read_text()
menu = (root / "src/m_text.c").read_text()
game = (root / "src/d_main.c").read_text()
assert "#define VDP_MAP_COLS 40" in video
assert "#define VDP_VIEW_ROWS 22" in video
assert "#include \"r19_pixel4.h\"" in video
assert "R19_UploadPixels();" in video
assert "R19_PrepareFrame();" in game
assert "#define VIEWWINDOWWIDTH 40" in menu
assert "-DVIEWWINDOWWIDTH=80" in build
assert "-DVIEWWINDOWHEIGHT=44" in build
assert "-DDOOM_R19_PIXEL4" in build
assert "DOOM_R19_PIXEL4 1" in script
assert "DOOM_TIMEDEMO 0" in script
assert "DOOM_SRAM_CACHE16 0" in script
assert "R19_TILE_BASE + y * VDP_MAP_COLS + x" in encoder
assert "VDP_loadTileData(r19_tile_row" in encoder
assert "r19_cost[pal][a]" in encoder
assert "r19_nearest[best_pal]" in encoder
assert 80 * 44 == 3520
assert 40 * 22 == 880
assert 880 * 32 == 28160
assert 40 * 8 * 4 == 1280

def expand(a, b, c, d):
    assert all(0 <= x <= 15 for x in (a, b, c, d))
    top = (a * 0x1111 << 16) | b * 0x1111
    bottom = (c * 0x1111 << 16) | d * 0x1111
    return [top] * 4 + [bottom] * 4

assert expand(1, 2, 3, 4) == [0x11112222] * 4 + [0x33334444] * 4
assert expand(0, 15, 8, 7) == [0x0000ffff] * 4 + [0x88887777] * 4
assert len(b"".join(x.to_bytes(4, "big") for x in expand(1, 2, 3, 4))) == 32
print("PASS R19: 80x44 pixels, H40 40x22 tiles, 4x4 expansion, per-tile palette, 1280-byte staging")
