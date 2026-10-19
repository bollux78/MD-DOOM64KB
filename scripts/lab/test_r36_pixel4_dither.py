#!/usr/bin/env python3
"""Host-side R36 Pixel4 tests. No 68000, WAD or runner required.

The full build additionally runs the real PLAYPAL quantizer and verifies the
output statistics. Here we test all 1024 pairs and the packed fifth-bit lane.
"""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("r36p4", ROOT / "scripts/lab/gen_r36_pixel4_dither.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Every possible combination of left/right 4-bit solid shades must reproduce
# the R22 original 8-pixel row exactly. All 5-bit combinations must be valid.
pairs = [(i, (i + 1) % 16) for i in range(16)]
even, odd = mod.make_row_tables(pairs)
assert len(even) == len(odd) == 1024
for key in range(1024):
    bits = key >> 8
    byte = key & 255
    left = (byte >> 4) + (16 if bits & 1 else 0)
    right = (byte & 15) + (16 if bits & 2 else 0)
    assert even[key] == mod.row_word(left, right, pairs, 0)
    assert odd[key] == mod.row_word(left, right, pairs, 1)
    if bits:
        assert all(0 <= (even[key] >> n) & 15 < 16 for n in range(0, 32, 4))

# Simulate all 3344 independent 4x4 samples in the 1672B legacy nibble plane
# plus exactly 418B for bit 4, then decode each 8-pixel scanline pair.
WIDTH, HEIGHT = 76, 44
packed = bytearray(WIDTH * HEIGHT // 2)
high = bytearray((WIDTH * HEIGHT + 7) // 8)
assert len(packed) == 1672 and len(high) == 418
for y in range(HEIGHT):
    for x in range(WIDTH):
        code = (x * 17 + y * 23 + (x * y % 31)) % 32
        index = y * WIDTH + x
        where = y * 38 + x // 2
        if x & 1:
            packed[where] = (packed[where] & 0xF0) | (code & 15)
        else:
            packed[where] = (packed[where] & 0x0F) | ((code & 15) << 4)
        mask = 1 << (index & 7)
        high[index >> 3] = (high[index >> 3] & (~mask & 255)) | (mask if code & 16 else 0)

for y in range(HEIGHT):
    for x in range(0, WIDTH, 2):
        index = y * WIDTH + x
        mask2 = (high[index >> 3] >> (index & 7)) & 3
        pair = packed[y * 38 + x // 2]
        recovered = [((pair >> 4) & 15) + (16 if mask2 & 1 else 0),
                     (pair & 15) + (16 if mask2 & 2 else 0)]
        expected = [(xx * 17 + y * 23 + (xx * y % 31)) % 32 for xx in (x, x + 1)]
        assert recovered == expected, (x, y, recovered, expected)
        key = mask2 * 256 + pair
        assert 0 <= key < 1024
        assert even[key] == mod.row_word(*recovered, pairs, 0)
        assert odd[key] == mod.row_word(*recovered, pairs, 1)

# Confirm the offline quantizer can actually choose 16 distinct useful
# checker mixtures when the input colors require them.
solids = [((i * 53 + 9) % 256, (i * 97 + 13) % 256,
           (i * 139 + 7) % 256) for i in range(16)]
original = [tuple((solids[a][c] + solids[b][c]) // 2 for c in range(3))
            for a in range(16) for b in range(a + 1, 16)]
original = (original * 3)[:256]
codes, chosen, report = mod.choose_colors(original, solids)
assert len(codes) == 256 and len(chosen) == 16
assert len(set(chosen)) == 16
assert report["checker_doom_colors"] >= 20
# R36b: the 418-byte high plane aliases the *tail* of the pending tilemap.
# The renderer writes map entries forward as it reads samples forward, and
# 4 spare map words (=8B) ensure no future high-plane byte is overwritten.
MAP_BYTES = 38 * 21 * 2 + 8
HIGH_BYTES = (WIDTH * HEIGHT + 7) // 8
HIGH_BASE = MAP_BYTES - HIGH_BYTES
assert MAP_BYTES == 1604 and HIGH_BYTES == 418 and HIGH_BASE == 1186
shared = bytearray(MAP_BYTES)
shared[HIGH_BASE:HIGH_BASE + HIGH_BYTES] = high
worst_gap = MAP_BYTES
for y in range(1, 22):
    for x in range(38):
        top_bit = (2 * y) * WIDTH + 2 * x
        bottom_bit = top_bit + WIDTH
        top = (shared[HIGH_BASE + (top_bit >> 3)] >> (top_bit & 7)) & 3
        bot = (shared[HIGH_BASE + (bottom_bit >> 3)] >> (bottom_bit & 7)) & 3
        assert top == ((high[top_bit >> 3] >> (top_bit & 7)) & 3)
        assert bot == ((high[bottom_bit >> 3] >> (bottom_bit & 7)) & 3)
        map_word = (y - 1) * 38 + x
        map_offset = 2 * map_word
        # The actual DMA map uses dynamic tiles in the two VRAM banks.
        tile = 16 + (map_word % 836)
        shared[map_offset:map_offset + 2] = tile.to_bytes(2, 'big')
        if (y, x) != (21, 37):
            next_top = 2 * y * WIDTH + 2 * (x + 1) if x < 37 else 2 * (y + 1) * WIDTH
            unread_byte = HIGH_BASE + (next_top >> 3)
            worst_gap = min(worst_gap, unread_byte - (map_offset + 1))
            assert map_offset + 1 < unread_byte, (y, x, map_offset, unread_byte)
assert worst_gap == 1, worst_gap
for tile in range(38 * 21):
    assert int.from_bytes(shared[tile * 2:tile * 2 + 2], 'big') == 16 + tile % 836
print("PASS R36b: in-place fifth-bit plane overlaps pending map safely; 8B RAM budget, minimum 1B gap")

print("PASS R36: all 1024 checker rows, 3344 samples, 418B high plane, 16 selected blends")
