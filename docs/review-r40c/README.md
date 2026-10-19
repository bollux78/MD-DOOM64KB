# R40c — Dual renderer runtime integration (WORK IN PROGRESS)

**This branch has no 8x8/4x4 runtime switch yet.** It is a safe development branch forked from the **user-approved R40b** pixel4 static-title/intermission anti-flicker build. Do not distribute as a dual-renderer ROM until real engine+video mode switching works.

## Verified prior work to integrate

- **R39f 8x8 (approved):** `r39f-dither3-vertical` (commit `e396c1c0c6850de795fda171da0a3cd37272505f`), Options > Dithering **Off / Checker / Vertical**. Keep all 8192 ROM colormap entries and 105 matching vertical tiles. [CI + ROMs](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39337772005/artifacts/12227047938).
- **R40b native 4x4 (approved):** `r40b-pixel4-text-diff` (commit `f78dc49678ee56bdc33e92eba2a52bb9b867face`), actual 76x44 samples packed 4bpp, 2 VDP banks. Critical `r22_map` bitset-alias anti-flicker fix for TITLEPIC/WIMAP0. [CI + ROMs](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39330509073/artifacts/12224755868).
- Base audio R39e: independent Music and SFX toggles, original PCM/XGM2, 8x8 dither API compatibility.
- Performance baseline: R40 fast 8x8 11.80 FPS/180.82 sec; R40 fast pixel4 3.01 FPS/708.37 sec, 2134 frames, stock 68000. R39f and R40b themselves have not received full timedemo values in the conversation.

## Plan

1. Merge R39f modifications **without overwriting** R40b `scripts/lab/build_r35_linear.fish` and `scripts/set_rom_identity.py` (both branched from R39e and independently modified these two files); first maintain two independent regression control builds.
2. Design an internal video dispatcher and true dynamic geometry for 38x22 and 76x44. The existing `#if DOOM_R22_PIXEL4` in `src/i_genesisv.c` and VIEWWINDOWWIDTH/HEIGHT/MAPWIDTH constants in `src/r_draw.c`, `src/r_plane.c` and projection/weapon lookup tables prohibit naive menu-only switching. Avoid per-sample dispatch in hot loops.
3. Reuse memory carefully: 4x4 framebuffer 1672 B, `r22_map` 1596 B; existing R40b anti-flicker bitmaps reuse first 210 B during native static images. 4x4 uses up to 1688 VDP tile indices (font at 1696); 8x8 uses 226 mixed/solid pattern tiles. Do not keep both VDP modes resident simultaneously; switch safely after DMA/VBlank completes. Palettes differ (8x8 4x16 versus 4x4 16).
4. Only after real mode availability implement Options `Render: 8x8 / 4x4`, queue mode request at menu event, apply between fully completed frames without resetting level/player, audio or map. Keep Dithering Off/Checker/Vertical for 8x8; preserve its state when pixel4 active; SFX/Music remain independent.
5. Produce playable dual ROM and isolated 8x8/4x4 DEMO3 variants from the unified source, test each full 2134-frame demo, boot, and manually run E1M1->E1M2, menu, CRT/real hardware after backup SRAM.

## Do not regress

- R39b distorted horizontally stretched textures and was rejected by user.
- R40a ghosting fix flashed because it wiped WINDOW per frame; **R40b** no-flicker occupancy diff is approved.
- Do not call two separately compiled ROMs a true runtime toggle.
- Keep MOVEP mall, real 76x44 sampling, Bayer8 320x224 static art, 52 PCM SFX, multi-XGM2, SRAM A130F1 switching and <=4 MiB linear ROM.

The full portable next-chat handoff is delivered separately as `DOOM_MD_HANDOFF_R39f_R40b_para_R40c.zip`.
