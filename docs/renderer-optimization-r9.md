# R9: geometry arithmetic on the stock 68000

HUD24 reference: 38×24 world, classic four-row status bar, 16-entry cache in WRAM, Fast DIVU + Color LUT, status-only DMA, NTSC 60 Hz, NO VSYNC. Reference measured on user BlastEm divider 7: 2134 DEMO3 frames, 9.39 FPS, 227.33 emulated seconds.

The R7 sample attributed 12.2% to R_StoreWallRange and 8.6% to R_AddLine, but those are 60 Hz VBlank samples, not accurate cycle profiling. Assembly fast paths must be compared against the C compiler's output rather than presumed faster.

## Matrix

| ROM | Difference |
| --- | --- |
| doom-md-hud-r9-base.bin | no R8 or R9 experiment switches |
| doom-md-hud-r9-slope.bin | guarded hardware DIVU.W for SlopeDiv16 ratio (n <= d) |
| doom-md-hud-r9-step.bin | guarded hardware DIVS.W for scale interpolation with quotient representable in signed 16 bits |
| doom-md-hud-r9-combined.bin | both options |

R_PointToAngle16 obtains slope indices by dividing an octant's smaller coordinate by its larger one. If n<=d and d!=0, (n*2048)/d always fits into 16 bits; a single DIVU.W computes the same integer result with truncation. When n>d use the exact original expression. The original wraps the quotient to uint16 before clipping, which is preserved in fallback.

R_StoreWallRange divides (scale2 - rw_scale) by a span of 1..37; signed 68000 DIVS.W is exact when quotient fits [-32768,32767]. A positive divisor width permits testing delta in [-32768*width,32768*width) before attempting DIVS.W. Fall back to original signed 32-bit division otherwise. Beware the CPU's signed quotient overflow if incorrectly bypassed.

Compilation includes mathematical boundary/random checks, individual identity stamped ROMs, full build flags, ELF objects and objdump disassembly where supported. Compilation validates the instructions; screenshots and DEMO3 execution are still required for behavioral verification.

Do not promote a change on negligible FPS differences. Compare all ROMs at 1000% emulator fast forward with original M68K divider 7, same 2134 frames and checks for graphical glitches. No change to display, textures, WAD, RAM allocation, SRAM or 13MHz mode.
