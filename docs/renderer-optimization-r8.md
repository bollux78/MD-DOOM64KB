# DOOM Mega Drive — R8 renderer experiments

Hardware: stock Sega Genesis 68000 at ~7.67 MHz (BlastEm divider 7), 38x24 3D and 4 text status rows, 60 Hz, no VSync. DEMO3: 2134 frames. Performance control: 9.39 FPS (227.33 s emulated).

The R7 sampling showed 24.0% SEG LOOP REST, 14.3% DRAW WALL, 12.2% STORE RANGE, 8.6% ADD LINE, and 6.1% CHECK BBOX. These are approximate exclusive VBlank samples, not cycle-accurate measurements.

## Sources consulted

- [Doom8088 column renderer](https://github.com/FrenkelS/Doom8088/blob/main/i_vcgabw.c): manually unrolled pixel writes and fixed-point texture stepping.
- [Original id Software DOOM assembly](https://github.com/id-Software/DOOM/blob/master/linuxdoom-1.10/README.asm): specialized texture mapping inner loops.
- [x68D00M](https://github.com/zz964/x68D00M): assembly column renderer / optimized blit; 68030/68060 instructions must not be copied to a stock 68000.
- [SpritesMind 68000 optimization thread](https://gendev.spritesmind.net/forum/viewtopic.php?t=2598): discussions of instruction costs, special cases, branches, addressing modes.
- [Doom 68k (Krikzz)](https://github.com/krikzz/doom-68k): arithmetic/render acceleration using FPGA, not directly relevant to stock MD.

## Five experimental ROMs

1. `doom-md-hud-r8-base.bin` — baseline, same flags as HUD24 9.39 FPS.
2. `doom-md-hud-r8-lut2.bin` — process two textured pixels per iteration in the existing fast Color LUT path.
3. `doom-md-hud-r8-lut4.bin` — process four pixels per iteration, same exact 16-bit wraparound.
4. `doom-md-hud-r8-masked.bin` — avoid computing wall-only reciprocal fracstep when the visible segment only contains a masked texture, retaining texturecolumn bookkeeping.
5. `doom-md-hud-r8-combo4.bin` — test interaction of lut4 and masked.

Avoid comparing profiler FPS with performance ROMs. Results must be tested in BlastEm with divider 7; user has validated that emulator fast-forward to 1000% does not change timedemo emulated results. All build flags are archived. No claim of speedup before measurement.

### Validation

Confirm 2134 frames, gameplay screenshot/texture fidelity, no crashes, same HUD and original geometry. Repeat any narrowly winning result. Inspect generated assembly before escalating the most promising strategy to hand-coded M68000 assembly.
