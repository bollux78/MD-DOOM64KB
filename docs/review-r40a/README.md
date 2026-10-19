# DOOM-MD R40a — Pixel4 native picture menu overlay fix

Base: r40-dual-renderer. Includes R39c MOVEP (cache + map), R39e independent Music/SFX toggles, and authentic R22 76x44 pixel4 raster.

## Bug reproduced in code
When static native R35 art (TITLEPIC, WIMAP0, HELP2) is showing, `R22_Text` wrote menu characters to WINDOW, skipping the per-frame overlay-clear logic applied over game raster. Previous cursor glyphs, slider ticks, and On/Off choices therefore accumulated. `I_FinishUpdate` returned early while native art was active, skipping `R22_EndOverlay` when menu disappeared. This does not occur over black gameplay background because the non-static path already manages WINDOW lifecycle.

## Fix
- When native art is active, clear WINDOW exactly once, immediately before fresh menu text of the frame. Preserve native Bayer8 picture on BG_A.
- Re-enable WINDOW when menu is drawn after the clear; mark the overlay as dirty.
- On a native-image frame without menu text, clear and hide the previous WINDOW overlay before returning, without reuploading the picture.
- Restrict text writing on the WINDOW to rows 0–21 to avoid the aliased SAT/HScroll address region beginning at 0xFC00.
- No change to native artwork, palettes, 3D renderer or SRAM/XGM2 paths; no intended FPS change.

## Tests
1. `doom-md-r40a-pixel4-play.bin`: while TITLEPIC is on-screen, open Start -> Options, change Dithering? Not present in native pixel4. Instead change Music and SFX repeatedly, move menu cursor up/down 10+ times and navigate to/from main menu. Check **no old cursors, slider dots or On/Off remnants**.
2. Close menu over TITLEPIC: the picture should remain clean, without lingering menu text.
3. Repeat on intermission/native artwork, if reachable.
4. Start E1M1: menu over black game background should behave as in R40, with sound options working. Return from menu, move camera, fire weapon; no corruption.
5. `doom-md-r40a-pixel4-perf.bin`: DEMO3 2134 frames, compare against R40-fast-pixel4-perf: 3.01 FPS, 708.37 seconds (stock 7.67 MHz).
6. Color observation: the legacy R22 font writer maps all menu text to palette 0. This change intentionally fixes ghosting first; it does not change native static picture palette entries to force red/yellow font colors.

The VDP/window fix is not exercised by the automatic 300-frame headless smoke. Manual title/menu testing is required.
