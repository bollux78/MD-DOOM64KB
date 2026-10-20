# R46 M3B — isolated real VDP 4×4 video boot diagnostic

Baseline: user-approved M3A, 3 ROMs functional. DEMO3 NTSC control
11.80 FPS / 180.82 s, M2C 11.78 FPS / 181.12 s, 2134 frames.

## Four variants in ONE CI artifact

1. **primary-perf**: unchanged R39f 8×8 control.
2. **m2c-perf**: full P2I/M3A helper set, R39f active.
3. **m2c-play**: playable 8×8 reference with unchanged active renderer.
4. **m3b-video-perf**: additional isolated real-hardware pixel4 VIDEO TEST.
   At boot it presents a true 76×44 packed framebuffer on the VDP for
   120 VBlanks (about 2 seconds in NTSC), then restores the original
   8×8 CRAM, tile patterns and tilemap and starts the normal DEMO3.
   No separate heap framebuffer, no permanently allocated tilemap.

## How the diagnostic works

- The P2I 1672-byte packed pixel framebuffer borrows the existing
  2128-byte `_s_screen` after the existing R20 pending DMA is drained.
- It retires old R20 VBlank snapshot publication, acknowledges the M3A
  QUIESCE protocol, clears Plane A and installs a temporary pixel4
  palette, then commits the P4 owner.
- All 798 dynamically packed tiles are loaded to **bank0** 54..851.
  All 21 graphics map rows are written to the existing BG_A 64×32
  tilemap, with 76-by-44 source samples and 38-byte packed pitch.
  The top two sample rows stay reserved for diagnostic font/text.
- VBlank/XGM system services continue while the visible test is shown.
- On exit, pixel4 ownership is revoked, DMA is drained, the original
  8×8 dither/stripe tiles and palette are rebuilt, BG_A is cleared, and
  R39f's 8×8 owner is committed. Only then is `_s_screen` initialized
  as the original tile-word framebuffer.

M3B is a **real VDP output exercise** using one bank only. No dynamic
double-buffer flip, native world traversal, texture sampling, weapon/sky
sprites, full UI adaptation, or in-game resolution toggle has been
implemented. The code is enabled **only** for the video diagnostic
ROM via DOOM_R46_M3B_DIAG. The three normal ROMs cannot call it.

## Testing / cautions

- Host oracle tests the actual packed-pattern generator against the
  M3A tile encoder: all 1596 tiles across two possible banks must
  be dynamic, valid and within bounds; the two reserved sample rows
  remain black; memory guards and owner-gated access are checked.
- GitHub CI builds and audits 4 ROMs. BSS may not exceed R39f control.
  BlastEm smoke tests all 4, including the isolated VDP diagnostic.
- User: verify the extra ROM visibly displays colored square patterns,
  transitions to original 8×8 after ~2 s, and DEMO3 proceeds without
  corruption or palette errors. Compare M3B timedemo with original
  11.80/11.78 references. Test PLAY separately.
- The diagnostic should be tested in BlastEm before deploying to
  flashcart/hardware; do not treat automated smoke as full pixel
  screenshot verification.

Next stage M3C: safe double bank presentation/VBlank map flip while
keeping the R39f path protected, then connect real Doom 4×4 projection
and masked draw once video ownership and upload cost are validated.
