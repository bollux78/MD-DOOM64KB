# Celso/MegalDoom HUD art V2 — isolated graphical experiment

## Prior findings

- Our Doom HUD Atlas V1 completed the 2134-frame DEMO3 at **9.29 FPS**,
  retaining the full 56-color world view.
- Palette-separation attempt PR #21 was rejected: it allotted PAL0-2 to
  HUD and confined the 3D scene to just 14 PAL3 colors. The world looked
  severely degraded. PR #21 was closed, unmerged.
- This experiment **does not change a single entry of the generated
  game palette** and does not alter the BSP renderer, Cache16 or DMA
  scheduling.

## Source from Celso Fontes

We reviewed the actual public
[megaldoom repository](https://github.com/celsowm/megaldoom):
`src/renderer/generated_hud_assets.h`,
`src/renderer/renderer_hud.c`, `src/renderer/renderer.c`,
`src/renderer/renderer_upload.c` and `tools/test-hud-layout.py`.

Static asset samples were extracted from the shipped generated header
into `assets/celso-megaldoom-hud-source.json`:

- Native **STBAR** tile art, cropped from 40×4 (320×32) to
  38×4 (304×32), omitting one 8px tile at each edge.
- Neutral Doomguy face frame, **4×4 tiles** (32×32).
- Full **16×16** red Doom digit canvases 0–9, 4 tiles per digit;
  compared with V1's smaller 8×16 screenshot numerals.
- Native **7×5** status-card art (three source images).
- Each source's palette as originally shipped by Celso.

Celso's source is licensed under **MIT**, © 2026 Celso Fontes.
Artwork extracted from original Doom assets remains subject to the
original artwork rights; MIT does not relicense the underlying images.

## Adaptation to our very different engine

`scripts/gen_celso_hud_art.py` converts source art at **build time**,
using our existing `genpal_cram[0]`. Every 8×8 tile selects the
closest existing among the four 16-color Mega Drive palettes, without
ever replacing or remapping the 56-color Doom world LUT.

211 resident tiles = 6752 bytes of VRAM:
152 background + 16 face + 40 numeral + 3 key.

The layout now puts larger 16×16 glyphs in three safe 6-column fields:
AMMO at columns 1..6, HEALTH at 9..14, ARMOR at 22..27, face at
17..20, keycards at 31,33,35. Numeric values, current-weapon ammo and
key state remain live. **This test uses fixed 16px digit spacing**:
native variable-width pixel-precise number composition is future work
and would introduce a different VDP upload strategy.

The renderer still calls exactly **one tilemap DMA**: 24 rows normally,
28 when status changed. No new runtime tileset streaming, dynamic
palette write, stack scratch buffer, SRAM, or extra VDP calls per frame.

## Fish build and emulator test

```fish
cd ~/Projetos
git clone --branch exp/68k-hud24-celso-art-v2 \
  https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-celso-art
cd doom-md-hud-celso-art
fish scripts/lab/run_celso_hud_art_test.fish

~/Projetos/blastem64-1.0.0/blastem \
  dist/celso-hud-art/doom-md-celsoart-perf.bin
```

Check first that the WORLD's colors resemble the 9.29 FPS control
and are not restricted to blocky red/green from PR #21. Then visually
assess the genuine STBAR, face, red numbers and keycards. If no
corruption, allow all 2134 frames and record average FPS. A screenshot
of the **in-game HUD** matters more than only the benchmark results.

Expected tradeoff: due to the fixed 56-color game palette, skin and
red still cannot be as faithfully rendered as in MegalDoom's **separate**
HUD palettes. This is deliberate. We can evaluate a more sophisticated
hybrid/dither later.

**Source prepared, not cross-compiled or BlastEm-tested by assistant.**
Never infer runtime stability from source checks alone. Keep V1 and
all stable HUD24/Fullscreen branches untouched.
