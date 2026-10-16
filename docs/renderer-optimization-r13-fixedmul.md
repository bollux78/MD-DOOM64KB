# R13: exact 68000 FixedMul arithmetic matrix

Reference: R12 LUT Full, user-measured 10.12 FPS, 210.95 seconds, DEMO3 2134 frames. Retain the entire R12 Full configuration, R11 TopLeftClip, R9 slope+step DIVU/DIVS and R10 distance DIVU. No projection, clipping, colors, tile resolution, or DMA changes.

## Rationale

`FixedMul` currently takes absolute values, decomposes them into unsigned 16-bit halves, performs 2 or 4 `MULU.W` operations, corrects negative-product rounding toward minus infinity, then negates the result. This experiment uses exact two's-complement decomposition instead of absolute values:

```
result = (ahi*bhi << 16) + ahi*blo + alo*bhi + (alo*blo >> 16)
       - (a < 0 ? blo << 16 : 0)
       - (b < 0 ? alo << 16 : 0)
```

Here the halves are **unsigned bit patterns** of the signed 32-bit operands. The result is modulo 2^32, identical to the original implementation's arithmetic shift behavior, including negative fractional results. Avoid a direct 64-bit multiply, which may invoke an expensive software helper on 68000.

| Variant | Implementation |
| --- | --- |
| r13-control | R12 LUT Full, original FixedMul |
| r13-mul4 | Four 16x16 unsigned multiplies, unconditional |
| r13-mulfast | Same but two multiplies if b fits positive 16 bits |
| r13-mulswap | Same, plus symmetric two-multiply path if a fits positive 16 bits |

Each experiment changes only `FixedMul`, which also serves sprites and wall geometry. Exhaustive representative 16-bit operands, signed extremes (excluding C-undefined `labs(INT_MIN)` in the original), and deterministic randomized 32-bit operands are compared to the original algorithm by `scripts/lab/test_r13_fixedmul.py` before build. The preflight does **not** establish frame-by-frame or real-hardware correctness.

## Evaluation

Run all four ROMs separately in the same BlastEm configuration: NTSC60, 68000 divider 7, 1000% fast-forward, DEMO3 2134 frames, 3x each. Compare total time and FPS and inspect visual integrity, especially sprite projection and walls. If faster, test actual gameplay and stock Mega Drive. No auto-selection or merge of experimental variants.
