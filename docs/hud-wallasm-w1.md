# Round W1 — textured WALL columns, 68000 assembly

Baseline: HUD24 38×24, status-only conditional DMA, 16-slot cache in RAM,
standard 68000 clock and no vsync. Previous measured non-profile ROM:
9.39 average FPS, DEMO3 = 2134 frames.

## Exactly one rendering change
- C: original \`R_DrawColumnWall -> R_DrawColumnSprite\`.
- ASM: replace only the inner loop for **textured wall columns** when the
  colormap points into the standard 32×256 WAD COLORMAP block. The assembly
  retains the original LUT mapping, 9-bit texture fractional shift,
  16-bit wrapping, 76-byte framebuffer row stride and original clipping.
- Invalid/nonstandard colormap remains on original C path.
- **Sprites, HUD, DMA, cache, palette, view dimensions, game logic unchanged.**
- Important: the 68000 version is hand-written for correctness first. It
  might be slower than GCC's C output. No speed improvement is assumed.

## Build exactly two ROMs

\`\`\`fish
cd ~/Projetos
git clone --branch exp/68k-hud24-wallasm-round1 \
  https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-wallasm
cd doom-md-hud-wallasm
fish scripts/lab/run_hud_wallasm_w1.fish
\`\`\`

Output: \`dist/hud-wallasm-w1/doom-md-wallw1-c-perf.bin\` and
\`dist/hud-wallasm-w1/doom-md-wallw1-asm-perf.bin\`.
Save build logs and ELF/symbols separately. Build script verifies that the
assembly feature flag actually reached the compiler, and did not leak into
the control ROM.

## Validation before FPS comparison
1. Both ROMs must compile.
2. Run the C control first in BlastEm 1.0.0: confirm 2134 frames.
3. Run ASM ROM, check wall colors/texture columns for glitches.
4. Wait for 2134 frames and compare FPS, same NTSC, no overclock.
5. On compiler error, share the last log lines. On error/black screen,
   stop and share screenshot. Do not run unvalidated ASM ROM on real console.

**Uncompiled and untested by assistant.** The original stable branch,
\`stable/hud24-text-9p29fps\`, Fullscreen and status-DMA branch are unchanged.
