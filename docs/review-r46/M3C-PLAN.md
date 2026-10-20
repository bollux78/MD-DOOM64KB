# DOOM-MD R46 M3C — Dual bank pixel4 VRAM boot diagnostic

User-approved M3B baseline: four ROMs working, M3B boot video showed correct
colored diagonals and returned to full 8x8 DEMO3. Measured: primary 11.80
FPS /180.82s, M2C and M3B 11.78 FPS /181.08s, 2134 frames, zero errors.

## Five ROMs in one automated artifact

- `doom-md-r46-primary-perf.bin`: approved 8x8 control.
- `doom-md-r46-m2c-perf.bin`: secondary helpers, actual renderer still 8x8.
- `doom-md-r46-m2c-play.bin`: usual full game and audio check.
- `doom-md-r46-m3b-video-perf.bin`: exact previously approved single-bank
  boot test, included again as video baseline.
- `doom-md-r46-m3c-video-perf.bin`: NEW dual-bank 4x4 diagnostic.

## Real M3C diagnostic

A new pattern generator produces **four consecutive color phases** in
a packed 1672-byte 76x44 frame temporarily borrowing the original
2128-byte `_s_screen`. No separate heap buffer or permanent pixel4
framebuffer. First two packed pixel rows stay reserved for the label.

A caller-owned protocol (`r46_m3c_bank.c`) prevents writing the currently
visible tile bank and will only commit the new bank after 798 uploads,
all 21 map-row acknowledgments, and an explicit VBlank/blank assertion.
These are software preconditions, not an automated electrical/VDP test.

The actual diagnostic (`r46_m3c_video.c`) uploads patterns into the
two physical VRAM banks, alternates bank0 / bank1 / bank0 / bank1,
displays each for 45 VBlanks, and returns to the normal R39f startup.

**Corrected SGDK VRAM layout (after M3C's first user test):**
bank1 dynamic tiles 890..1687 occupy VRAM 0x6F40..0xD2FF and
overlap **BG_B at 0xC000**, NOT BG_A. The project's 64x32 SGDK layout
already has **BG_A at 0xE000..0xEFFF**. M3C initially aborted with
"Unexpected BG_A base" because it assumed the inverse placement.

- Keep BG_A at **0xE000** throughout the diagnostic, and explicitly
  require its original address. Redirect **BG_B** from C000 to E000
  temporarily so it cannot interpret the bank1 patterns as tilemap
  entries; both planes point to the same valid diagnostic name table.
- While the display is disabled, restore **BG_B to C000**, clear its
  overwritten names, clear BG_A at E000, rebuild the original 8x8
  dither/stripe patterns and restore original CRAM before resuming.
- If SGDK has unexpectedly moved BG_A or BG_B away from E000/C000,
  abort instead of risking an unseen overlap.

M3C's first five-ROM CI passed compilation and smoke tests, but the
user correctly observed a runtime failure at boot. The updated build
adds host checks for both plane addresses and their restoration.

**Important limitation: this is NOT seamless zero-blanking VBlank
page flipping.** H40 BG_A map origins are 0x2000 aligned, and we
currently have only one safe 64x32 map. The code performs hidden-bank
pattern uploads with the old bank still visible, then *disables display*
while updating all 21 map rows, waits another VBlank, commits the bank,
and reenables video. Short black flashes during swaps are expected.
The test aims to avoid mixed-bank tearing, not yet to eliminate blanking.
M3D may need a revised VRAM layout/VDP plane strategy for seamless swaps.

Performance implications: each new bank has 798 dynamic tiles, or
**25,536 tile-pattern bytes** plus 1,596 name-table bytes. They are CPU
uploads in this diagnostic, NOT a production VBlank DMA budget.
The time to upload is not included in timedemo FPS because these are
blocking boot tests before DEMO3 starts. Do not infer continuous
60 Hz native 4x4 refresh from the M3C benchmark.

## Gates

- Host C test: 4 phases x 798 tiles, all dynamic, exact 76x44 nibble
  layout, memory guards, stage/visible-bank exclusion and map commit
  checks; source audit for BG_B mirroring, both plane addresses, mask and restoration.
- GitHub CI: build 5 ROMs, check LTO symbols and feature flags,
  audit BSS control <= baseline and diagnostic <= baseline+16 bytes,
  header/size/hash, 300/480 frame BlastEm smoke.
- User: watch M3C show 4 shifting diagonal-color phases (possible
  momentary black frames at transitions), finish restoring 8x8, and
  complete DEMO3. Compare all 5 ROMs, especially the M3B control
  and M3C video test. Do not flash to hardware until tested on BlastEm.

The native Doom BSP, walls, flats, sprite texture columns, sky, HUD,
weapon and gameplay 4x4 dispatcher are still separate. They are NOT
drawn in this diagnostic.
