#!/usr/bin/env python3
"""R118: host check that the r47_mul.h helpers equal libgcc __mulsi3 (low 32 bits) for every operand
shape used by DOOM_R47_MUL_LOGIC / DOOM_R47_MUL_BSP and the R118 P_DivlineSide change.
68000 semantics: MULU.W = u16 x u16 -> u32, MULS.W = s16 x s16 -> s32."""
import random

M = 1 << 32
def s32(v): v &= M - 1; return v - M if v >> 31 else v
def s16(v): v &= 0xFFFF; return v - 0x10000 if v >> 15 else v
def asr(v, n): return s32(v) >> n            # arithmetic shift of an int32
def mulu16(a, b): return ((a & 0xFFFF) * (b & 0xFFFF)) & (M - 1)
def muls16(a, b): return (s16(a) * s16(b)) & (M - 1)

def r47_mul32x16(a, b):                      # r47_mul.h, transcribed
    a &= M - 1; b = s16(b)
    lo = a & 0xFFFF; hi = s16(a >> 16)
    low = mulu16(lo, b)
    if b < 0: low = (low - (lo << 16)) & (M - 1)
    high = muls16(hi, b)
    return s32(low + (high << 16))

def mulsi3(a, b): return s32(s32(a) * s32(b))

rng = random.Random(118)
edge32 = [0, 1, -1, 0x7FFFFFFF, -0x80000000, 0x10000, -0x10000, 0xFFFF, -0xFFFF, 0x7FFF0000, -0x7FFF0000]
edge16 = [0, 1, -1, 0x7FFF, -0x8000, 0x100, -0x100]
n = 0
for _ in range(400000):
    a = rng.choice(edge32) if rng.random() < 0.05 else rng.randrange(-2**31, 2**31)
    b = rng.choice(edge16) if rng.random() < 0.05 else rng.randrange(-2**15, 2**15)
    assert r47_mul32x16(a, b) == mulsi3(a, b), (a, b)                  # int32 x int16 (R47 paths)
    x, y = rng.randrange(-2**31, 2**31), rng.randrange(-2**31, 2**31)
    p, q = asr(x, 16), asr(y, 16)                                      # (int32 >> 16): always int16
    assert -0x8000 <= p <= 0x7FFF and -0x8000 <= q <= 0x7FFF
    assert s32(muls16(p, q)) == mulsi3(p, q), (x, y)                   # R118 P_DivlineSide
    d = s32(x - y)                                                     # (y - node->y) wraps like C int32
    assert s32(muls16(asr(d, 16), q)) == mulsi3(asr(d, 16), q)
    n += 3
print('R118 mul helpers exact: %d cases' % n)
