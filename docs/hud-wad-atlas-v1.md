# Doom HUD Atlas V1 — first real artwork test

Branch based on PR #19's working Doom-inspired 4-row HUD:
**9.26 FPS, 2134 DEMO3 frames**, BlastEm NTSC 60 Hz, normal 68000.

## Artwork source, honestly identified

The reduced `scripts/doom64.wad` may lack the usual Doom UI patches.
At build time, `scripts/gen_doom_wad_hud.py` probes the WAD and uses:

- `STBAR` (320×32 cropped to 304×32), if present in ordinary
  Doom picture-patch format;
- `STFST00` (or STFST01/02), neutral face if present;
- `STTNUM0..9`, red number glyphs if all ten are present.

**When any of these assets are absent or use an unsupported format,
that specific component falls back to art from the original Doom sprite
atlas image provided in the conversation.** The fallback atlas was
downsampled and embedded as three compact text assets (not invented
pixel art): `assets/doom-hud-*.b85`. The generator prints which source
was actually used for background, face and digits.

This is a real-Doom-art test, not yet a pixel-perfect reproduction of
STBAR, and not yet Dither Lab output.

## Hardware pipeline

- 38×24 3D display and exactly 4 HUD tile rows (304×32).
- All 188 image tiles (152 background, 16 static 32×32 portrait,
  20 numeral tiles) are generated at build time using existing
  `genpal_cram[0]` as the VDP palette target.
- For each tile, the best of PAL0..PAL3 is chosen, with 4-bit indices.
  The VDP gets **6016 additional bytes of 8×8 tiles** at startup.
- No new sprite objects, CRAM entries, cartridge SRAM, big WRAM
  buffers, or additional DMA in the rendering loop.
- **Still exactly one conditional tilemap DMA**: 24 rows normally,
  28 when health/armor/current weapon ammo/weapon/keycards/gamestate
  changes, as on PR #19.
- Dynamic red numerals: current weapon ammunition, health and armor.
  Keycard indicators still use font B/Y/R on V1. Face fixed/neutral.

## One ROM build

```fish
cd ~/Projetos
git clone --branch exp/68k-hud24-doom-atlas-v1 \
  https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-atlas
cd doom-md-hud-atlas
fish scripts/lab/run_doom_wad_hud_v1.fish
```

Run:

```fish
~/Projetos/blastem64-1.0.0/blastem \
  dist/doom-hud-atlas/doom-md-wadhud-v1-perf.bin
```

First visually inspect the original Doom face, numbered ammo/health/
armor fields and 304×32 metal strip. If correct, finish DEMO3 and
record total frames/FPS. Compare with 9.26 FPS for Doom-style mockup and
9.39 FPS for text HUD. Stop immediately if rendering is black or corrupt.

**Source committed; binary not compiled or emulator-tested by assistant.**
The original stable HUD24, graphical gauge HUD and Fullscreen lines are
untouched. Do not merge until the new experiment passes.

Potential aesthetic compromises: 304×32 crop/resizing from the user
screenshot fallback, 4-color status background and 16-color source face,
per-VDP-tile existing-palette quantization and reduced 8×16 red digits.
Dither Lab can refine these later.
