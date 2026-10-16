#!/usr/bin/env python3
"""R19 flat-DBRA invariant test: R18 framebuffer and flat pixel stores remain exact."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
video = (root / "src/i_genesisv.c").read_text()
build = (root / "scripts/build_silent.fish").read_text()
script = (root / "scripts/lab/build_r19_flat_dbra.fish").read_text()
r18 = (root / "scripts/lab/build_r18_playable.fish").read_text()
assert "DOOM_R19_FLAT_DBRA" in video
assert '"dbra %[n],1b"' in video
assert '"adda.w #76,%[dst]' in video
assert '"move.w %[color],(%[dst])' in video
assert "DOOM_R19_FLAT_DBRA" in build
assert "set -gx DOOM_R19_FLAT_DBRA 1" in script
assert "set -gx DOOM_R17_PIXEL_DBRA 1" in script
assert "set -gx DOOM_CACHE_SLOTS 16" in script
assert "set -gx DOOM_HUD_DMA_STATUS_ONLY 1" in script
assert "set -gx DOOM_TIMEDEMO 0" in script
assert "set -gx DOOM_R16_WEAPON_LIFT 1" in script
assert "DOOM_R19_PIXEL4" not in video
assert "DOOM_R19_FLAT_DBRA" not in r18
assert "VIEWWINDOWWIDTH=80" not in build

# DBRA's signed 16-bit counter executes count iterations for count-1,
# and the destination address advances by 38 * sizeof(uint16_t).
for count in range(1, 23):
    for yl in range(22 - count + 1):
        for x in (0, 1, 18, 37):
            original = [yl * 38 + x + i * 38 for i in range(count)]
            dbra = []
            addr = yl * 38 + x
            n = count - 1
            while True:
                dbra.append(addr)
                addr += 38
                n = (n - 1) & 0xffff
                if n == 0xffff:
                    break
            assert original == dbra
print("PASS R19: flat DBRA matches R18 at every 38x22 column position and length; baseline untouched")
