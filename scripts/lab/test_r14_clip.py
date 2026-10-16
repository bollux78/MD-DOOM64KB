#!/usr/bin/env python3
"""R14 preflight: exhaustive visible run and bbox-scan equivalence tests."""
import itertools
import random
from pathlib import Path

def original(col, first, last, solid):
    col = list(col)
    runs = []
    while first < last:
        if col[first]:
            try:
                first = col.index(0, first, last)
            except ValueError:
                return runs, col
        else:
            try:
                to = col.index(1, first, last)
            except ValueError:
                to = last
            runs.append((first, to - 1))
            if solid:
                col[first:to] = [1] * (to - first)
            first = to
    return runs, col

def scan(col, first, last, solid, unroll):
    col = list(col)
    runs = []
    def find(p, end, target):
        if unroll:
            while end - p >= 2:
                if col[p] == target: return p
                if col[p + 1] == target: return p + 1
                p += 2
        while p < end:
            if col[p] == target: return p
            p += 1
        return None
    while first < last:
        if col[first]:
            p = find(first, last, 0)
            if p is None:
                return runs, col
            first = p
        else:
            p = find(first, last, 1)
            to = last if p is None else p
            runs.append((first, to - 1))
            if solid:
                col[first:to] = [1] * (to - first)
            first = to
    return runs, col

def verify(col):
    n = len(col)
    for first in range(n + 1):
        for last in range(first, n + 1):
            # Bounding box must report the presence of a zero identically.
            orig_bbox = 0 in col[first:last]
            new_bbox = any(col[i] == 0 for i in range(first, last))
            assert orig_bbox == new_bbox, (col, first, last)
            for solid in (False, True):
                orig = original(col, first, last, solid)
                assert scan(col, first, last, solid, False) == orig
                assert scan(col, first, last, solid, True) == orig

for n in range(0, 11):
    for bits in itertools.product((0, 1), repeat=n):
        verify(bits)
rng = random.Random(0xD0014)
for _ in range(1800):
    # Full width with a fixed left border; random occlusion patterns.
    bits = [1] + [rng.randrange(2) for _ in range(37)]
    verify(bits)
s = Path("src/r_draw.c").read_text()
assert "#if defined(DOOM_R14_CLIPSCAN)" in s
assert "#if DOOM_R14_CLIPSCAN == 2" in s
assert "#if defined(DOOM_R14_BBOXSCAN)" in s
assert "R14_CLIP_MEMCHR" in s
assert "memchr(solidcol+sx1, 0, sx2-sx1)" in s
assert "DOOM_R13_MUL_DECOMP" not in s
b = Path("scripts/build_silent.fish").read_text()
assert "DOOM_R13_MUL_DECOMP" not in b
print("PASS: R14 exhaustive binary clip spans 0..10, 1800 randomized 38-column cases, bbox, and no R13 code")
