# 24-row game DMA with persistent 4-row black text HUD

**Base**: stable-looking 38x24 classic text HUD branch, PR #12.
The 3D viewport remains 38x24 cells and is unchanged; no SRAM.

## Baseline vs experiment
- `hud24`: the already-tested build, sends all **38x28** tilemap cells every frame.
- `dma24`: sends only **38x24** gameplay cells per frame.
  Separately compares each of the four HUD tilemap rows to the previously
  uploaded version; uploads a row if it has changed (including on first frame).
  The status bar is therefore not lost and dynamically updates life/armor/ammo.
- Same framebuffer RAM footprint; snapshot of HUD adds 304 bytes static RAM.
- The fixed HUD starts at row 24 and never covers the 3D viewport.
- Full DMA was 1064 tilemap cells/frame. Normal split DMA is 912
  cells/frame after initial HUD transfer, i.e. 14.29% less **tilemap data**,
  not an automatic 14% FPS increase.
- Heads-up: CPU compares up to 152 HUD cells each frame, and tilemap DMA
  call overhead may eliminate any speed benefit. Measure empirically.

## Build / run
```fish
cd ~/Projetos
git clone --branch exp/68k-classic-hud-dma24 \
  https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-dma24
cd doom-md-hud-dma24
fish scripts/lab/run_hud_dma24.fish
```
Outputs `dist/doom-md-hud-dma24.zip` with four ROMs
(`hud24-perf`, `dma24-perf`, `hud24-stats`, `dma24-stats`).

Compare both PERF ROMs in BlastEm 1.0.0 NTSC, divider 7, 2134 DEMO3
frames. The old `hud24` benchmark previously yielded 9.29 FPS;
re-run the control under the same conditions. Verify text values still
update and black strip stays fixed, including menus. STATS optional
after both PERF complete.

**Source-only change; not compiled or runtime-tested remotely.**
Do not merge until validated locally.
