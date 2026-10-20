# DOOM-MD R42 Q2 — first isolated 4×4 wall-kernel experiments

**Important:** Q2 is a separate branch from R40c dual integration. Parent is the user-approved `r40b-pixel4-text-diff` and preserves its title/intermission anti-flicker patch, MOVEP, audio and native 76×44 4bpp geometry.

## Why we are testing this
R41 VBlank statistical profiling of DEMO3 completed 2134 frames:
- R41 control: 3.01 FPS, 709.67 sec;
- R41 profiled: 2.90 FPS, 735.85 sec (3.69% instrumentation overhead);
- wall draw: 46.3% of VBlank **samples**; other-column loop: 10.5%; flat: 8.8%; sprite/fuzz: 2.8%; VRAM upload: 11.9%. VBlank sampling is not cycle-exact, and IRQ-masked DMA can bias these values.

R22 does not use the 8×8 `R20_RegColumn` or `FLAT_INLINE` kernels; `src/r22_video.inc` explicitly `#error`s if the 8×8 flags are active. Q2 works directly on **76×44 independent pixels**, packed two 4bpp samples per byte, with stride **38**.

## ROMs
1. `doom-md-r42-control-p4perf.bin` — bit-identical original R40b wall code path, no Q2 macros.
2. `doom-md-r42-hoist-p4perf.bin` — optimized C: perform x/y border bounds **once**, adjust 16-bit texture fraction for skipped rows, write directly at 38-byte row strides with one nibble mask determined outside the loop.
3. `doom-md-r42-asm-p4perf.bin` — same C hoisting and address calculations, with inline MC68000 `move.b`, `andi.b`, `or.b`, `move.b` sequence for every individual framebuffer store; no 8×8 kernel reuse.
4. `doom-md-r42-asm-p4play.bin` — playable asm variant to verify menu/intermission, monsters, texture colors, collision/gameplay and actual CRT visuals.

**Warning:** Inline assembly only optimizes the packed byte store, not the entire column source/colormap loop. It may be **slower** than optimized C despite the wall-draw share. Do not assume a gain: compare all three performance ROMs and prefer the winner. The large '5–6 FPS' goal was a speculation, not a predicted result.

The assembler version uses read-modify-write, not OR-only over existing pixels. It preserves high nibble for odd x and low nibble for even x. Clipping and player weapon/sprites stay on their own original C draw paths. No runtime audio/palette/menu changes.

## Test procedure
- GitHub Actions compiles all four with the **same pinned shareware WAD**, XGM2, signed PCM, maps, optimized MOVEP mall, native Bayer8 art; verifies linear ROM <=4MiB and headless 300 frames.
- Native C oracle script `scripts/lab/test_r42_wall.py` runs **20,000 randomized wall columns** (independent x parity, negative coordinates, screen-clipped spans, level/nonlevel, mapped/unmapped color, random nonzero starting bytes, canary bounds), comparing the optimized C and the reference per-pixel C output byte for byte. Inline asm is cross-compiled and must be verified visually on BlastEm; native host oracle cannot execute M68k instructions.
- Run all three timedemos to 2134 frames in BlastEm at **stock NTSC 68000 speed** (not 13 MHz OC). Save average FPS, min/max and time. Baseline R40b/R41 = 3.01 FPS, 709.67 sec. Keep table of actual screenshot results.
- Play the asm variant through E1M1 and E1M2; check walls with overlaid enemies/sprites/weapon, doors, masked textures, flats, HUD and R40b native static-title/intermission text. Compare screenshot against original at approximately same camera view; no flicker or ghosts.
- If asm fails CPU speed or visual equivalence, keep hoisted-C test and revert ASM; never merge unverified output into R40c. Once one variant wins and matches visuals, consider a second dedicated `R22_DrawColumnFlat` asm experiment, only after measuring.

The branch does not contain the future dual-runtime `Render 8x8/4x4` toggle. R40c development should proceed separately and may selectively port a Q2 winner after validation.
