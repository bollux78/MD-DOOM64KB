# R57 runtime H32/H40 and independent H/V crop menu

Base 6680d21d3137dc82b3311138963d11b285328f42. Fixed c55-a6 palette.

Main ROM: doom-md-r57-view-play.bin. In Options, use Left/Right or A:
Video mode H40/H32; H crop 0/8/16/24/32; V crop 0/8/16/24/32.
VIEW WWWxHHH shows effective physical raster dimensions. Values are per
edge. H40 base is the original visible 296x168 raster. H32 base is 256x168;
horizontal crop there is ADDITIONAL to fitting the game into H32. Values
are retained when toggling modes. All settings live in RAM for the session.

H40 defaults 16/16 -> 264x136. H32 with 16/16 -> 224x136.
H40 32/32 -> 232x104. H32 32/32 -> 192x104. H32 0/16 -> 256x136.

Changing mode/crop mid-game uses the Start/Options menu, then resumes the
same level without restart. UI/static title/intermission/results stay H40.
Requested H32 applies after closing the menu; a display/TV resync blink is
possible. HUD is full in H40 and compact H/A/AMMO in H32. The existing
Benchmark menu entry uses the selected settings and returns to the menu.

Geometry is computed once per setting change. Bounds clip BSP columns,
wall/flat/sprite samples and DMA, keeping the original 76x44 packed buffer,
projection/texture steps and immutable Pair-V tile patterns. Independent
X/Y bounds fix the former implicit square-crop assumption. H32 scrolling
remains A=-24/B=-20, H40 A=0/B=4; a smaller H32 raster has side margins.

Setter waits for the queued frame BEFORE mutating geometry; geometry then
remains stable while DMA is pending. A transition invalidates border state;
excluded cells are cleared and expanded areas refill on the next render.
Mode switch retires the old frame, blanks display, completes DMA, switches
width, clears the planes, disables the old full-screen Window mask, restores
scroll and invalidates cached HUD text. This explicitly preserves plane A
when returning from H40 menu to H32 gameplay.
No new heap allocation or SRAM writes. Seven configuration bytes in data.

Five newly built ROMs:
view-play: interactive menu, H40 default16/16.
h40c16-perf: H40 16/16; h40c32-perf: H40 32/32.
h32c0-perf: H32 0/16; h32c32-perf: H32 32/32.
The PERF presets exercise the SAME runtime-capable renderer as PLAY.

Host checks: all 50 mode/H/V combinations compile actual raster functions
and compare scalar texture sampling, clipping, framebuffer guards and DMA
source bounds. Actual menu setter is exercised for 300 queued-frame
changes; actual mode-switch function for 32 menu/demo/level transitions,
including stable-mode no-op checks. Existing legacy pixel4 oracle retained.
CI audits ROM/BSS bounds and runs four PERF presets at 800/30000 emulated
frames. Normal exit is not proof of a correct screen or completed timedemo.
Manual hardware checks: repeated H40/H32 changes and independent H/V
extremes, close/reopen Options, HUD/weapon, automap and next-map transition.
