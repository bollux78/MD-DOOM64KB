# R12: bit-exact 68000 wall reciprocal lookup experiment

**Verified reference:** R11 TopLeftClip, 10.07 FPS, 212.02 s, 2134 frames, DEMO3 NTSC60 (user measurement). Preserve R9 slope+step, R10 distance, R11 top+left clips, 38-wide framebuffer, 24-row 3D projection, 4-row bottom HUD, 16 composed-column slots, no vsync.

## Hypothesis

In `R_RenderSegLoop`, the fast path calculates the 16-bit 7-bit-shifted reciprocal of the projected wall scale via `DIVU.W`:
`(0xffffffffu / scale) >> 7 == 0x01ffffffu / scale` for 512 <= scale <= 65535. The table of these exact 16-bit quotients is stored in cartridge ROM. A ROM lookup may be cheaper than a 68000 `DIVU.W` (variable instruction latency), but ROM bus and extra range checks also cost cycles. Benchmark before concluding.

No approximations, rounding changes, or geometry changes. Fallback is the exact original R11 implementation for values outside the table. All 65024 eligible divisors are checked against the original expression before building.

## Variants

| ROM | Table | Wall path | Masked midtextures |
| --- | ---: | --- | --- |
| r12-control | none | R11 DIVU.W | R11 original reciprocal |
| r12-lut4k | 7 KiB, 512..4095 | lookup in range | unchanged |
| r12-lut16k | 31 KiB, 512..16383 | lookup in range | unchanged |
| r12-lutfull | 127 KiB, 512..65535 | lookup in range | unchanged |
| r12-lutfullmasked | same 127 KiB | lookup | lookup in range |

These are ROM sizes for the LUT alone, not final binary sizes. Generator is `scripts/lab/gen_r12_recip_lut.py`; generated `src/r12_recip_lut.h` is gitignored. Runner builds five ROMs and publishes logs, compiler flags, ELF and disassembly. Static preflight verifies all eligible scale values, not in-game screenshots.

## Test

Same BlastEm NTSC60 divider7 and 1000% fast-forward, DEMO3 2134 frames. Run each 3x; compare average FPS, 15s min/max, runtime and image integrity (especially sky, sprites, masked walls). Test the fastest visually correct candidate on stock Mega Drive before adopting. Watch cartridge ROM size and cartridge read latency; larger LUT may be slower.
