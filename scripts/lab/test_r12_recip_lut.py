#!/usr/bin/env python3
"""Exhaustive mathematical and structural preflight for R12 LUT experiment."""
from pathlib import Path
from gen_r12_recip_lut import value, VALID, MIN

# R11's quotient is (0xffffffff/scale)>>7, equivalent to
# floor(0x01ffffff/scale). Check all 65024 legal 16-bit divisors.
for scale in range(MIN, 65536):
    expected = (0xFFFFFFFF // scale) >> 7
    actual = value(scale)
    assert actual == expected, (scale, actual, expected)
    assert 0 <= actual <= 0xFFFF
for limit in VALID:
    assert value(limit) <= 0xFFFF
    assert limit - MIN + 1 in (3584, 15872, 65024)
s = Path("src/r_draw.c").read_text()
assert 'r12_recip_table[(uint16_t)scale - 512u]' in s
assert '#if defined(DOOM_R12_RECIP_LUT)' in s
assert '#if defined(DOOM_R12_RECIP_MASKED)' in s
assert 'FixedReciprocal(scale) >> COLEXTRABITS' in s
assert 'uint32_t quotient = 0x01ffffffu;' in s
assert 'DOOM_R11_LEFTCOL_CLIP' in s
assert 'DOOM_R11_TOPBAR_CLIP' in s
print("PASS: R12 exhaustive 65024-entry equivalence, 3 table sizes, fallbacks, and R11 guards")
