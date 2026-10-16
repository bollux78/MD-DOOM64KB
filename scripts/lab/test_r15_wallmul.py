#!/usr/bin/env python3
"""R15: bit-exact signed 16x32 -> 16.16 wall-product preflight.

The original 68000 expression is a signed 32-bit product (low 32 bits),
arithmetic shifted right by 16. Do NOT replace it with a 64-bit product:
overflow/wraparound behavior would change Doom's pixels.
"""
import random
from pathlib import Path

MASK32 = 0xFFFFFFFF

def s32(v):
    v &= MASK32
    return v - 0x100000000 if v & 0x80000000 else v

def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v

def original(a, b):
    return s16(s32(a * b) >> 16)

def mul_u(a, b):
    ua, ub = a & 0xFFFF, b & MASK32
    low = ua * (ub & 0xFFFF)
    high = ua * (ub >> 16)
    product = (low + (high << 16)) & MASK32
    if a < 0:
        product = (product - (ub << 16)) & MASK32
    return s16(s32(product) >> 16)

def mul_s(a, b):
    high = a * s16(b >> 16)
    low = abs(a) * (b & 0xFFFF)
    fractional = -((low + 65535) >> 16) if a < 0 else low >> 16
    return s16(high + fractional)

def check(a, b):
    expected = original(a, b)
    u = mul_u(a, b)
    s = mul_s(a, b)
    assert u == expected and s == expected, (a, b, expected, u, s)

b_edges = (-2147483648, -2147483647, -1073741824, -65537, -65536,
           -65535, -32768, -1, 0, 1, 32767, 65535, 65536, 65537,
           1073741824, 2147483646, 2147483647)
for a in range(-32768, 32768):
    for b in b_edges:
        check(a, b)

rng = random.Random(0xD0015)
for _ in range(220000):
    a = rng.randrange(-32768, 32768)
    b = rng.randrange(-2147483648, 2147483648)
    check(a, b)

src = Path("src/r_draw.c").read_text()
build = Path("scripts/build_silent.fish").read_text()
assert src.count("R15_TAN_PRODUCT(rw_distance, tan)") == 4
assert "rw_distance = R15_SETUP_PRODUCT(hyp," in src
assert "rw_offset = R15_SETUP_PRODUCT(hyp," in src
assert "product -= ub << 16;" in src
assert "R15_Mul16x32Shift16S" in src
assert "DOOM_R15_TANMUL" in build and "DOOM_R15_SETUPMUL" in build
for forbidden in ("DOOM_R13_MUL_DECOMP", "DOOM_R14_CLIPSCAN", "DOOM_R14_BBOXSCAN"):
    assert forbidden not in src and forbidden not in build, forbidden
print("PASS: R15 1,114,112 edge products + 220,000 seeded signed 16x32 cases; no R13/R14")
