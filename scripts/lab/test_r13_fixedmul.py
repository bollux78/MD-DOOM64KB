#!/usr/bin/env python3
"""R13 exact 16.16 multiply preflight: original magnitude/rounding vs new 16x16 products."""
import random
from pathlib import Path

MASK = 0xFFFFFFFF

def signed32(v):
    return ((v + 0x80000000) & MASK) - 0x80000000

def old_fixed_mul(a, b):
    # Reference: r_draw.c FixedMul; avoid INT32_MIN (C labs undefined).
    neg = (a ^ b) < 0
    a, b = abs(a), abs(b)
    al, ah, bl, bh = a & 65535, a >> 16, b & 65535, b >> 16
    ll = ((al * bl) + (65535 if neg else 0)) >> 16
    value = ah * bl + ll
    if bh:
        value += (ah * bh << 16) + al * bh
    return signed32(-value if neg else value)

def r13_fixed_mul(a, b, mode):
    ua, ub = a & MASK, b & MASK
    alo, ahi = ua & 65535, ua >> 16
    blo, bhi = ub & 65535, ub >> 16
    if mode >= 2 and bhi == 0:
        result = ahi * blo + ((alo * blo) >> 16)
        if a < 0:
            result -= blo << 16
    elif mode >= 3 and ahi == 0:
        result = bhi * alo + ((blo * alo) >> 16)
        if b < 0:
            result -= alo << 16
    else:
        result = ((ahi * bhi) << 16) + ahi * blo + alo * bhi + ((alo * blo) >> 16)
        if a < 0:
            result -= blo << 16
        if b < 0:
            result -= alo << 16
    return signed32(result)

def check(a, b):
    expected = old_fixed_mul(a, b)
    for mode in (1, 2, 3):
        got = r13_fixed_mul(a, b, mode)
        assert got == expected, (a, b, mode, expected, got)

edges = (-2147483647, -1073741824, -65537, -65536, -65535, -32768, -1, 0,
         1, 2, 32767, 32768, 65535, 65536, 65537, 1073741824, 2147483647)
for a in edges:
    for b in edges:
        check(a, b)
for a in edges:
    for b in range(-32768, 32769, 17):
        check(a, b)
rng = random.Random(0xD0013)
for _ in range(160000):
    a = rng.randrange(-2147483647, 2147483648)
    b = rng.randrange(-2147483647, 2147483648)
    check(a, b)
# All small positive and negative b with representative wall heights/scales.
for b in range(-65535, 65536):
    check(0x12345678, b)
    check(-0x12345678, b)
source = Path("src/r_draw.c").read_text()
assert "#if defined(DOOM_R13_MUL_DECOMP)" in source
assert "mulu(ahi, bhi)" in source
assert "if (bhi == 0)" in source
assert "if (ahi == 0)" in source
assert "#endif /* DOOM_R13_MUL_DECOMP */" in source
print("PASS: R13 exact signed FixedMul variants, negative fractions, overflow, edge values and 16-bit operands")
