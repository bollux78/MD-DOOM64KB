# R40 — native 4x4 feasibility baseline (stage 1 of a genuine runtime 8x8 ↔ 4x4 switch)

Base: `r39e-audio-toggles`, original 8x8 R39c mall MOVEP, R39d ON/OFF dithering, R39e music and sound effects.

**This stage is NOT yet a runtime renderer switch.** It assembles and measures both existing Doom renderer backends with the same game/episode/audio and current SRAM optimizations. Do not add a "4x4" menu item until the hardware/runtime transition actually exists.

## ROMs
- `doom-md-r40-cell-play.bin` = authentic 38x22 viewport 8x8 3D, 38x28 VDP buffer, R39c mall, checker dither toggle, Music/SFX toggles
- `doom-md-r40-cell-perf.bin` = its clean DEMO3 baseline, compare R39e 11.80 FPS
- `doom-md-r40-base-pixel4-perf.bin` = authentic R22 76x44 4x4 3D framebuffer, original SRAM copying but Music/SFX toggle code compiled
- `doom-md-r40-fast-pixel4-perf.bin` = same native R22 4x4 and presentation, using SRAM `MOVEP` map/cache ("mall")
- `doom-md-r40-fast-pixel4-play.bin` = playable 4x4 renderer with Music/SFX toggles

The 4x4 renderer has 76x44 **independent projected samples**, packed nibble framebuffer and two VDP tile banks. It is **not** an enlarged 38x22 viewport, and its screen palette is different. The 8x8 dithering menu item is only available in the 8x8 build. Music/SFX toggles do work in both.

## Why this stage is necessary
- `src/i_genesisv.c` chooses mutually exclusive whole video implementations with `#if DOOM_R22_PIXEL4`.
- 8x8 is a tileword framebuffer (`_s_screen`), word lookup tables and 38x22 geometry; 4x4 is packed pixel buffer (`r22_fb`), 76x44 renderer and VDP expansion/upload.
- `VIEWWINDOWWIDTH`, `VIEWWINDOWHEIGHT`, `MAPWIDTH`, view angle and scale lookup tables are compile-time constants in multiple engine files, not only a video presentation parameter.
- There is no safe quick switch while frames are in flight, and two separately compiled ROMs are not a runtime menu toggle.
- Before designing a dual backend one must validate memory margins, fps, palette/VDP recovery after static native art, crash/stability and SRAM cart constraints.

## Next stage: real switch
Refactor renderer projection/tables to choose 38x22 or 76x44 per level/frame, max-size arrays where safe, and separate per-mode framebuffers/VDP code. All transitions must wait for DMA and VBlank handoffs; video resources must be reinitialised only between completed frames and never mid-interrupt. Menu requests a pending mode change; it commits after leaving the menu, not inside the draw callback. No level/map reload or loss of gameplay state permitted. Add explicit tests on CRT/EverDrive after reliable BlastEm tests. Until this is completed, report only the two authentic standalone modes.

## Testing
1. Timedemo all three PERF ROMs at stock CPU; report FPS, time and full 2134 frames.
2. In 4x4 PLAY check menu/titles, E1M1/E1M2 geometry, music/SFX ON/OFF, PAL/CRAM, HUD, screenshots, no black screen or corruption.
3. Compare pure 8x8 with R39e (11.80 FPS) for regression.
4. Measure pixel4 R40 control vs pixel4 R40 mall to validate the MOVEP advantage.
5. Keep linear ROM 4MiB and R31's SRAM mapper switch. Backup SRAM on hardware.
