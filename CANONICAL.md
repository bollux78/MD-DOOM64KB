# MD-DOOM64KB — HUD

**Canonical HUD line**, restored directly from the stable
`exp/68k-hud24-dma-status-only` source commit
`00d827692476f95c04b9bd22ec431279da2bad61`,
before all graphical HUD experiments.

- 3D viewport: **38x24** cells plus 4-row text HUD (38x28 output).
- Cache16 in **work RAM**, no cartridge SRAM.
- Single conditional tilemap DMA per frame:
  24 rows normally; 28 when health/armor/bullet count changes.
- **No graphic HUD assets, Celso art or custom 8x8 HUD tiles**.
- **No routine profiling**: `hudprofile-perf` measured ~9.36 FPS,
  but `hudstatus-perf` without profiling measured **9.39 FPS**.
- Verified historical DEMO3: **2134 frames**, 227.33s,
  NTSC 60Hz BlastEm normal 68000 speed.

Rebuild only this reference:

```fish
fish scripts/lab/build_hud.fish
~/Projetos/blastem64-1.0.0/blastem dist/hud/doom-md-hudstatus-perf.bin
```

The wrapper preserves all original HUD24 renderer/cache logic.
Only the canonical one-ROM build script and explanatory docs are new.

Repository branch policy: retain only `fullscreen` and `hud`.
