# HUD24: Single-DMA conditional height diagnostic

The original 38x24 viewport + four-row black text HUD completed DEMO3:
- HUD24 baseline 28-row DMA: **9.29 FPS**, 2134 frames.
- DMA24 **no HUD writes**: **9.39 FPS**, 2134 frames.
- DMA24 plus additional HUD DMA calls: emulator stuck/glitches.
- DMA24 plus CPU HUD writes after gameplay DMA: black screen.

This change uses **exactly one** `VDP_setTileMapDataRect` call every frame:
- if HUD tile contents (4x38 tilemap cells) changed, upload 28 rows;
- otherwise, upload 24 gameplay rows.
- first frame always uploads all 28.
- no additional VDP accesses are made by the HUD.
- 304-byte RAM snapshot of previous HUD tile values; render still 38x24.
- No SRAM changes. Normal HUD text and gameplay remain unchanged.

Build only one diagnostic ROM:
```fish
cd ~/Projetos
git clone --branch exp/68k-classic-hud-single-dma \
  https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-single-dma
cd doom-md-hud-single-dma
fish scripts/lab/run_hud_single_dma.fish
~/Projetos/blastem64-1.0.0/blastem dist/hud-single-dma/doom-md-singledma-perf.bin
```

Test visually before benchmarking: HUD appears at startup and text fields
update on ammo/health changes; DEMO3 should complete 2134 frames.
No result should be called stable before emulator validation.
