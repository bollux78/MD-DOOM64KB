# R17 — MC68000 pixel-loop optimization (R16 Hand1 base)

## Verified baseline

R16 **Hand1**: Mega Drive 7.67 MHz + Magnavox CRT, **10.20 FPS** in DEMO3. BlastEm divider 7: **10.33 FPS / 206.58 s**. R16 Hand2 also 10.20 FPS on real hardware but Hand1 selected for visual framing. R16 control 10.16 FPS / 210.03 s. All R16 variants passed hardware and emulator tests.

Do not change R16 geometry, HUD 2-row lift, first-person weapon +1 row, 38x22 viewport, top and left clips, 16-slot RAM cache, R12 65535-entry reciprocal LUT, or R15 setupu multiplication.

## Hypotheses

**R17 DBRA:** `R_DrawColumnSprite()` is used by both wall and sprite columns, and the hot standard COLORMAP path executes one iteration for each rendered vertical cell. Replace only that loop with a compact MC68000 inline assembly `DBRA` loop. Preserve exact 16-bit fraction wrapping, 9-bit texture coordinate shift, byte-indexed texel, 16-bit VDP tile word and 76-byte row stride. Leave the nonstandard-colormap fallback in C.

**R17 FRAC MULU:** The starting fraction is cast to 16 bits, so only the low 16 bits of `(yl - CENTERY) * fracstep` matter. Use a single `MULU.W` and keep the low word. This is exact modulo 65536 for negative and positive deltas.

| ROM | Initial frac | Pixel loop |
|---|---|---|
| r17-control | Original R16 Hand1 | Original C |
| r17-fracmul | MULU.W low16 | Original C |
| r17-dbra | Original R16 Hand1 | DBRA assembly |
| r17-combined | MULU.W low16 | DBRA assembly |

## Verification

Python preflight exhaustively compares **851,968** MULU low-word products (13 deltas × 65,536 steps) and simulates 20,000 randomized vertical columns against the original C behavior. These tests do **not** execute the actual 68000 instructions: the GitHub runner only proves compilation, not hardware stability.

Benchmark all four ROMs with BlastEm NTSC60, divider7, DEMO3 2134 frames, and visually inspect walls, sprite animation, weapon, palette and sky. Re-run best results before hardware. Reject any ROM with crashes or color artifacts, even if faster. Keep R16 Hand1 as reference until verified.
