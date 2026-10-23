# R57 viewport crop16 experiment

Base: 7e6a6e4aa87c734a7b422fe0597a9d66d0e28a88 (R57 Werk color lab).
User requested 2 tiles = 16 physical pixels removed from EACH visible edge.
All four ROMs use the SAME c55-a6 table; this is not a new palette selection.

- viewport-full-play/perf: original R57 gameplay rectangle.
- viewport-crop16-play/perf: actual early renderer and Pair-V DMA clipping.

The existing safety border excludes samples x<2 and y<2. Original visible
rectangle [2,76) x [2,44) is 296x168 physical pixels. Crop rectangle
[6,72) x [6,40) is 264x136 physical pixels. Physical output rectangle:
x=24..287 and y=24..159, both inclusive, in the unchanged video mode.
This removes exactly 16 pixels from each *visible* edge, including the
asymmetric original margins. It is a crop, not downsampling or stretching.

Projection tables, center, texture stepping, 4x4 samples, packed 76x44
framebuffer and assembly strides are unchanged. The view is narrower;
central scene scale/proportions are preserved. SRAM/audio/game tic rates,
static artwork, menus, HUD and classic 8x8 backend are unchanged.

The crop marks horizontal edge columns solid BEFORE BSP wall-range work,
clips top/bottom opening arrays before walls/sky/flats, restricts sprite
column traversal and guards every packed raster path. Only visible columns
and rows are DMAed: 33x17 words per plane instead of 38x21. Framebuffer
clears and some BSP/sprite setup costs remain unchanged; expect measured
gains to differ from the percentage area reduction.

The excluded tilemap cells are cleared on level entry; native artwork
transitions already clear both planes. The transfer rectangle is queued
with the completed framebuffer, not derived from changing game state in
VBlank. No new heap allocations; only two byte flags added.

Compare full-perf against crop16-perf, same emulator/hardware/settings.
Both run the same DEMO3. PLAY needs manual checks: title, map menu, game,
Start menu close/reopen, automap, intermission and next-map transition.
Full timedemo wall-clock and visual validation are pending until tested.
The 30000-frame headless regression covers 500 emulated seconds, but exit
code zero alone cannot prove correct graphics or a completed result screen.
