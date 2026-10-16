# MegalDoom technical comparison and isolated palette test

Based on public [celsowm/megaldoom](https://github.com/celsowm/megaldoom), under
the MIT License (Copyright 2026 Celso Fontes). MegalDoom is a separately built
Doom-inspired engine, not a drop-in module for the low-memory Doom64KB port.

## Evidence in the Celso source

- `src/renderer/renderer.c`, `load_game_palettes()`: separate palette
  lines PAL0 HUD steel/keys, PAL1 red numbers, PAL2 face, PAL3 world.
- `src/renderer/renderer_hud.c`: correct native Doom number *pixel anchors*
  and widths rather than rendering each number into an 8px-wide glyph;
  dynamic values only update when dirty.
- `renderer_hud.c`: 32x32 portrait using a 16-tile VRAM streaming window;
  the 21 baked expression frames deduplicate 258 source tiles.
- `renderer_hud.c`: numbers and keycards temporarily composed on stack to
  avoid consuming precious static WRAM/SGDK heap. It uses dedicated WINDOW
  plane, BG_B HUD background and BG_A 3D view because its scrolling,
  layered renderer differs fundamentally from ours.
- `renderer_upload.c`: handles dirty tile runs, upload budgets, background
  VBlank pump and optional sparse framebuffer. This is **not** safe to
  transplant wholesale into our one-conditional-DMA tilemap design.
- `src/renderer/generated_hud_assets.h`: HUD generated from original
  `STBAR.png`, `STF*.png` and Doom number patches; the source game-art
  still carries its original rights. Do not confuse Celso's MIT source
  license with permission to redistribute id Software art.

## Our first *isolated* implementation

This branch starts from our WAD/atlas HUD V1 experiment (9.29 FPS reported
by user on normal BlastEm) and ports **one idea only**: palette material
separation. Our `genpal.py` previously let a HUD tile choose among the
four world palettes individually, degrading steel/face/digit quality.

Now an opt-in build uses PAL0 for metal, PAL1 for red digits and PAL2 for
skin/face. The HUD asset converter restricts all tiles of each material
to that bank, using their colour ramps; **PAL3 remains dedicated to 3D**.

### Important cost/tradeoff, don't hide it

Our existing renderer has 56 distinct viewport colours spread over all
four palettes. Reserving PAL0..PAL2 for the HUD means **only 14 colour
slots remain for the 3D view**. We remap all 256 Doom input indices to
the existing 14 PAL3 world colours in the generated `genpal_cell`
table, preventing wrong-palette wall colours but reducing viewport
colour fidelity. This is a VISUAL EXPERIMENT, not a free upgrade.

Same 38x24 viewport, same cache16 in main RAM, same 24-or-28-row
single conditional tilemap DMA. No extra VDP calls each frame. No
changes to Doom raycasting, BSP traversal or wall drawing.

The next logical steps *only if the comparison is favourable* would be:
1. pixel-precise dynamic number placement/cropping from Celso HUD
   (instead of naive 8x16 numeral spacing); 
2. static neutral face from his tile data / a WAD patch with improved
   palette fidelity;
3. only later: different DMA architecture, sparse uploads, or BSP tricks.

We should favour a **hybrid** over forcing all status bars into 3
palettes when gameplay 56-color fidelity matters.

## Test

```fish
cd ~/Projetos
git clone --branch exp/68k-hud24-celso-palettes-v1 \
  https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-celso
cd doom-md-hud-celso
fish scripts/lab/run_celso_hud_palette_test.fish
~/Projetos/blastem64-1.0.0/blastem \
  dist/celso-hud-test/doom-md-celsohud-v1-perf.bin
```

Inspect the entire scene and HUD, not only completion FPS. Compare
against original HUD Atlas V1 (9.29 FPS): skin/metal/digits quality and
world scene losing 56→14 colour slots. Do not promote unless the
tradeoff is clearly worthwhile. No assistant-side ROM compile yet.

## Attribution and compatibility

Our port's existing GPL headers remain GPL; the material palette
*strategy* is a general implementation idea. When copying substantive
MIT source verbatim, retain Celso's MIT copyright + permission notice.
The experiment uses our own palette-ramp code rather than copying any
Celso image or compiled graphics bytes. Original Doom art retains its
underlying rights regardless of source-code licensing.
