# R15 — optimize expensive wall texture multiplication (R12 Full base)

**Discard R13 and R14.** Restore original `FixedMul`, `R_ClipWallSegment`, `R_CheckBBox`, all R12 Full compiler flags, R11 symmetric 38x24 display, and R12 exact reciprocal table. Measured stable reference: **10.12 FPS / 210.95 seconds**, DEMO3 2134 frames on stock-clock Mega Drive emulation.

## Hypothesis

The main `R_RenderSegLoop` computes `(rw_distance * tan) >> 16` **once per visible textured column**. `rw_distance` is 16-bit signed, but `tan` is 32-bit signed, so a generic 32x32 multiply can be expensive on the 68000. `R_StoreWallRange` also uses two similar products per segment for distance and texture offset.

Replace **only these exact products**, not the globally shared `FixedMul` (R13 crashed). The 68000 lacks a single-instruction 32x32 multiply; split into two 16x16 operations and preserve the original **low 32-bit product**, signed arithmetic shift by 16, and signed-16-bit output. This is not the same as a 64-bit product shifted by 16.

- **Unsigned decomposition**: `lo = MULU(a_lo,b_lo)`, `hi = MULU(a_lo,b_hi)`, `product = lo + (hi<<16)`; when a is negative, subtract `b<<16` for sign extension; return signed `product>>16`.
- **Signed-high decomposition**: `high = MULS(a,b_hi)`, `low = MULU(abs(a),b_lo)`; for negative a, round the low term toward negative infinity; return the low signed 16 bits of the result.

| ROM | Per-column tangent | Per-segment setup |
| --- | --- | --- |
| r15-control | original R12 | original R12 |
| r15-tanu | unsigned decomposition | original |
| r15-tans | signed-high decomposition | original |
| r15-setupu | original | unsigned decomposition |
| r15-setups | original | signed-high decomposition |
| r15-bothu | unsigned decomposition | unsigned decomposition |
| r15-boths | signed-high decomposition | signed-high decomposition |

`scripts/lab/test_r15_wallmul.py` tests all 65,536 signed distances against 17 boundary 32-bit tangent values (1,114,112 pairs), plus 220,000 deterministic random cases, comparing the exact low32-bit result of the original multiplication. The runner builds all variants, checks ROM headers, compiler flags and R12 compatibility, and publishes disassembly and ELF for profiling.

## Benchmark

BlastEm NTSC60, divider 7 (stock 7.67MHz), DEMO3 2134 frames, fast-forward up to 1000%. Run all seven once and repeat any promising or suspicious variants three times. Verify no black screens, no wall or sky glitches, correct sprites/doors, then check real hardware before adoption. Keep the R12 Full baseline until there is a clear repeatable improvement.
