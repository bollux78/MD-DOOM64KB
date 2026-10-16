# HUD24 graphical status test

Isolated non-SRAM visual experiment, based on the **known-good HUD24
status-only conditional DMA** branch (9.39 FPS; 2134 DEMO3 frames).

## What it changes

- Only the **four HUD tile rows**, at Y=24..27, become graphical.
- **Three 10-cell bars**: red HEALTH (0..100), yellow ARMOR (0..200),
  grey BULLETS (0..200); numeric fields remain visible.
- Uses existing SGDK font tiles and `SOLID_TILE_INDEX + 15` in the
  three reserved text palettes. **No new VRAM tiles, no new palette
  entries, no extra DMA, no SRAM.**
- Preserve the existing 38x24 3D framebuffer, the original 16-slot RAM
  cache, status-only dirty state (health/armor/bullets/level) and exactly
  one 24-or-28-row tilemap DMA per frame.
- The bars are test art, *not* the final Doom face/status artwork.
- Redshift/damage palette changes can alter the apparent bar color,
  because existing reserved palette entries are reused.
- Ammo bar represents **bullets only**, not the selected weapon ammo.

The classic HUD branch and Fullscreen branch are unchanged.

## Build one ROM

```fish
cd ~/Projetos
git clone --branch exp/68k-hud24-graphic-test \
    https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-graphic
cd doom-md-hud-graphic
fish scripts/lab/run_hud_graphic_test.fish
```

Output: `dist/hud-graphic-test/doom-md-hudgfx-perf.bin`.

Run in BlastEm 1.0.0, NTSC 60 Hz, divider 7. Immediately check graphics
and HUD placement; if working, wait for all 2134 frames and record FPS.
Do not test on physical hardware until emulator validation.

**Prepared source only. Not compiled or emulated by the assistant.**
