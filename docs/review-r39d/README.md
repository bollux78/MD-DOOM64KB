# R39d — Live DITHER ON/OFF in the 8x8 Doom renderer

Base: `r39c-sram-ab`, with `mall` (MOVEP for texture cache plus map data) enabled in all three R39d A/B builds.

## Functionality
- **PLAY:** Start opens main menu; enter **Options > Dithering: On/Off**. Press **A** to toggle. It takes effect after leaving the menu, with no level restart.
- Default ON is the exact R35d 50% checkerboard lookup: no four-column stretching (R39b remains discarded).
- OFF selects the original `genpal_cell` solid tiles for walls, floors, ceilings, sky, sprites, and weapon.
- Static/full-screen native Bayer graphics remain unchanged (R30 artwork is not the 3D renderer).
- Both 16 KiB 32x256 ROM lookup tables are generated from the same COLORMAP and 256-color palette; the matching solid and checker `colorcell` tables are included in ROM. No per-pixel mixing or new framebuffer.
- **PERF:** The toggle code/tables are compiled but the menu is inaccessible during automated DEMO3. It starts ON, so the two `cell-perf` ROMs can quantify any runtime selector overhead. Do not mistake this for the FPS of DITHER OFF; OFF requires an additional static or benchmark variant.
- No persistence across a console power cycle. Existing SRAM map/save contents remain unchanged.

## Experiment ROMs
1. `doom-md-r39d-control-cell-perf.bin`: R39c mall without runtime toggle, reference ~11.80 FPS.
2. `doom-md-r39d-toggle-cell-perf.bin`: R39c mall plus runtime LUT selection, default DITHER ON.
3. `doom-md-r39d-toggle-cell-play.bin`: playable with Options toggle.

## Tests
- Run both `cell-perf` DEMO3 to completion, 2134 frames; confirm same sequence, similar FPS.
- In PLAY, select E1M1 and verify **On** checker tiles vs **Off** solid tiles (no horizontal stretching, same geometry).
- Flip ON/OFF more than once in the same session, navigate back to game, verify flats, sprites, masked walls, sky, SFX.
- Rotate camera and change level to verify that cached colormap lookups are correctly invalidated.
- Back up EverDrive SRAM/save before hardware testing of experimental MOVEP variants; validate on BlastEm first.
