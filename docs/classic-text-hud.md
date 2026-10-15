# Classic Doom viewport + black text HUD — first experiment

Isolated branch `exp/68k-classic-hud-viewport` based on renderer Round 4,
**no cartridge SRAM** and no unstable R6/R7 SRAM assembly.
No changes to main or the existing stable ROMs.

## Design
- Full baseline: 38 columns × 28 rows 3D, no extra HUD.
- Classic variant: **38 × 24** 3D rows + **four reserved black rows**
  displayed by SGDK background tilemap, still 38 × 28 visible.
- Status strip at row 25: **HEALTH / ARMOR / BULLETS** text values; row
  27: DOOM — MEGA DRIVE. These are ordinary font tiles with a solid
  black background, not composed into the 3D renderer.
- Note BULLETS is actual `player.ammo[am_clip]`, not the current
  weapon's ammunition. This is a deliberately minimal text mockup.
- Original `ST_Drawer` (which drew over the 3D viewport) is omitted
  in the classic variant only; redshift/palette behavior remains.
  `HU_Drawer` and menus still run normally.
- The framebuffer allocates 28 rows in both variants, because the
  bottom strip is included in the VDP DMA. This first experiment
  measures savings from drawing 24 3D rows, **not** framebuffer savings.
- VDP upload still transfers 28 rows; optimizing static bar transfer
  separately can be considered after this version is stable.

## Build
```fish
cd ~/Projetos
git clone --branch exp/68k-classic-hud-viewport \
    https://github.com/bollux78/MD-DOOM64KB.git doom-md-classic-hud
cd doom-md-classic-hud
fish scripts/lab/run_classic_hud.fish
```

Outputs `dist/doom-md-classic-hud.zip` with four ROMs
(`full28-perf`, `full28-stats`, `hud24-perf`, `hud24-stats`)
and RAM reports.

## Verification protocol
1. Run `doom-md-hud-full28-perf.bin` in BlastEm 1.0.0 (NTSC 60 Hz,
   original 68000 clock divider 7); confirm 2,134 DEMO3 frames.
2. Run `doom-md-hud-hud24-perf.bin`, check 3D ends exactly above
   black status strip and labels update correctly, then record FPS.
3. Compare stats variants only if both perf variants complete. Cache
   requests/hits **need not match** since viewport size changes.
4. Check the screenshot visually before any physical hardware trial.

This is a source experiment only; no cross-compilation or emulator
runtime validation was possible in the assistant environment.
