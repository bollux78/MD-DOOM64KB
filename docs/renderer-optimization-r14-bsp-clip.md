# R14: R12-based BSP visibility and clipping scan experiments

**R13 is discarded**. This is based on the *R12 LUT Full* code and build flags, including its original `FixedMul`. No R13 arithmetic code or R13 build flags are present. Reference measured by user: R12 Full, **10.12 FPS / 210.95 s**, DEMO3 2134 frames, BlastEm NTSC60, stock 7.67 MHz 68000.

The R7 profiling pointed at BSP traversal, wall storage and per-column rendering as expensive stages. R14 focuses on two very short (38-column) visibility searches that currently call `memchr` repeatedly:

- `R_ClipWallSegment`: first solid/non-solid pixel; alternatives inline scalar or pair-unrolled search, preserving the exact first match and identical `R_StoreWallRange` calls.
- `R_CheckBBox`: determine if any unsolid pixel exists between `sx1` and `sx2`, using a bounded scalar scan instead of `memchr`.

No approximate math, tile-count change, geometry simplification, color change, DMA modification or extra framebuffer. The pair-unrolled version reads two **bytes**, never unaligned 16-bit words (important on 68000).

| ROM | Wall clip search | BSP bbox search |
| --- | --- | --- |
| r14-control | original memchr | original memchr |
| r14-clip1 | scalar inlined | original memchr |
| r14-clip2 | pair-unrolled | original memchr |
| r14-bbox | original memchr | scalar inlined |
| r14-clip1bbox | scalar inlined | scalar inlined |
| r14-clip2bbox | pair-unrolled | scalar inlined |

`scripts/lab/test_r14_clip.py` checks visible run ranges and solid column changes against the original algorithm for every 0/1 pattern up to 10 pixels, plus 1,800 randomized 38-pixel windows; also checks bbox first-zero existence. This does not replace testing on BlastEm or stock Mega Drive.

Run each ROM **three times**, individually, with divider 7 / NTSC60 / DEMO3. Check 2134 frames, average FPS, elapsed time, walls, masked textures, sprites and crash behavior. Reject unstable versions and tiny non-repeatable differences. Preserve the best stable reference.
