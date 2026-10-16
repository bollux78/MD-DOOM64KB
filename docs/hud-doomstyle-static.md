# Doom-style HUD (static placeholder) — one ROM experiment

Starting point: HUD24 38×24 viewport with four HUD tile rows, Cache16
in main RAM and the empirically tested **one DMA per frame** strategy:
24 rows normally, 28 on status changes. DEMO3 baseline: **9.39 FPS**,
2134 frames in BlastEm 1.0.0 (NTSC 60 Hz, original 68000 speed).

This experiment **does not** extract the Doom STBAR or STFACE graphics
from the WAD. It is deliberately a temporary approximation in the
classic 304×32 pixel layout, so we can test hardware/resource stability
before adding WAD-derived art.

## Display layout (38 columns × 4 rows)

- 4-row metal-styled backing, bevels and separator ribs.
- 4×4-tile / 32×32-pixel **fixed, monochrome Doomguy-inspired portrait**
  in the center (not animation, not the original STFACE).
- **AMMO**: ammunition for the currently selected weapon
  (`weaponinfo[readyweapon].ammo`); zero for weapons without ammo.
- **HEALTH**: current player health.
- **ARMOR**: armor points.
- **KEYS**: B, Y, R status from `player.cards[0..2]`.
- **WEAP**: currently selected weapon ID.
- 20 new 8×8 graphic tiles generated **once at boot**:
  4 metal patterns + 16 portrait tiles. These require 640 bytes of VRAM,
  not new frame-buffer RAM, and use existing PAL3/15 gray and black.
- Existing fonts and colors reused; no CRAM modification.
- Only a few bytes added to persistent DMA change detection:
  weapon and three-bit key mask. It invalidates the HUD when a
  displayed field changes; no extra calls to VDP_setTileMapDataRect.
- Existing 38×24 3D renderer and frame upload remain unchanged.

## Build & test

```fish
cd ~/Projetos
git clone --branch exp/68k-hud24-doomstyle-static \
    https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-doomstyle
cd doom-md-hud-doomstyle
fish scripts/lab/run_doomstyle_hud_test.fish
~/Projetos/blastem64-1.0.0/blastem \
    dist/doomstyle-hud/doom-md-doomhud-perf.bin
```

Stop if there is a black screen, corruption, or crash. If graphics
look right, let DEMO3 finish all 2134 frames and compare against
9.39 FPS. This version is **source only, not cross-compiled or run
by the assistant**. Keep physical-console testing until after emulator
validation.

The baseline HUD24, graphical-gauge experiment, and Fullscreen remain
unchanged.
