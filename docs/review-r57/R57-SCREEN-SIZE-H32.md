# R57 screen-size menu / H32 experiment

Base c6c313f6a5358e3f4ccd9490e8d9794f654e4f9b. Fixed c55-a6 palette.

- size-play: H40, Options > Screen size toggles Full / Crop16, default Crop16.
  Selection is in RAM for this session, not written into cartridge SRAM.
  Same projection/texture sample locations, actual early clipping and DMA
  rectangle changes; no framebuffer allocation or expensive video reinit.
- crop16-perf: fixed H40 264x136 crop control, like previous vp-crop16-perf.
- h40n-play/perf: fixed H40 256x136 narrow control.
- h32-play/perf: SAME 256x136 source samples as h40n, but real H32 during game.

H32 source rectangle is samples [6,70) x [6,40). DMA remains at original
64-cell plane stride and tilemap coordinates. Horizontal scrolling A=-24,
B=-20 moves the 256-pixel ROI to screen x=0..255, preserving the +4-pixel
Pair-V separation. H40 narrow uses A=0/B=4 at x=24..279. Packed framebuffer,
assembly strides, palettes and sampling tables are unchanged.

Both narrow H40 and H32 use the same compact H/A/AMMO HUD and FPS position; in H32, text is placed relative to the
screen despite the scrolled planes. Title, intermission, menus and results
remain H40 to preserve existing full-resolution static art and readable
text. Width switches occur between completed frames, with display blanked,
VDP DMA completed and planes cleared; no HBlank tricks. Native-art exit
reapplies the H32 scroll values. Returning from a menu invalidates HUD
cached values so all HUD text is redrawn. A visible mode-switch blink or
TV resync on hardware is possible and requires manual testing.

Comparison: h40n-perf vs h32-perf isolates video mode at equal render area.
Previous full-perf vs crop16-perf measures the useful area reduction.
H32 is not assumed faster. Sega Genesis Software Manual DMA table gives
memory-to-VRAM VBlank capacity of 167 bytes/line H32 vs 205 H40. Smaller
visible raster can save CPU work, but H32 itself reduces transfer capacity.
Source: https://nemesis.hacking-cult.org/MegaDrive/Documentation/GenesisSoftwareManual.pdf

Checks: scalar oracle compiles actual packed wall/sprite/flat code with
fixed crop, narrow crop and dynamic Full/Crop16; guards and transfer source
bounds checked. CI compiles six ROMs, audits ROM/BSS limits and checks
three PERF ROMs with 800 and 30000 emulated frames. Process exit success
is not proof of correct graphics or a result screen; manual validation
must include toggling size repeatedly, menus, automap and map transitions.
