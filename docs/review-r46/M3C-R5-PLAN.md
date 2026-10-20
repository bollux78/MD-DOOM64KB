# R46 M3C R5 — Heap lifetime isolation after SGDK research

## Starting point

The branch is created **directly from `r46-m3c-r3-font-restore`**, the
version whose dual-bank R3 SAFE/STRESS rendered correct text and
completed DEMO3 in an earlier user screenshot. Other later M3C
branches are **not merged**. Latest R4/R4B tests had black/red screens
and are NOT valid sources for continued integration. The original
single-bank M3B is the last fully accepted VDP baseline.

## Root facts verified against SGDK (not assumptions)

- With `LEGACY_FONT_LOCATION=1`, default SGDK 64x32 H40 maps:
  BG_A=E000, BG_B=C000, Window=D000, font=(C000/32-96)*32 =
  B400..BFFF.
- M3C tile banks: 0 = tile 54..851, 1 = tile 890..1687
  (=6F40..D2FF). Bank1 writes over both BG_B names, Window name
  entries and **all original 96 font tiles**.
- SGDK `VDP_setBGBAddress` and `VDP_setWindowAddress` call
  `updateMapsAddress(FALSE)`; when the minimum map origin changes,
  SGDK unpacks/reloads `font_default`, invokes `MEM_pack()`, and may
  defragment sprite VRAM if its sprite engine is initialized.
- Reading `src/memory.c` establishes that `MEM_pack()` compacts
  adjacent FREE blocks, **not live allocations**. The first invalid
  R20 buffer header must be measured; `MEM_pack()` alone is not
  proof of why the 2128-byte heap snapshot was lost.
- Both R3 variants restored visible text, but R28 displayed
  `ERRORS=2` and unexpected `RAW FREE=3514` against the
  Primary `ERRORS=0`, `RAW FREE≈1386`. Bit 2 corresponds to the
  original 2128-byte heap snapshot header no longer equaling 2131.
- R4B direct VDP register writes produced solid red screen
  after an error. That result is NOT evidence that the native
  double bank layout itself is impossible.

Source links:
- https://github.com/Stephane-D/SGDK/blob/master/src/vdp.c
- https://github.com/Stephane-D/SGDK/blob/master/src/memory.c
- https://github.com/Stephane-D/SGDK/blob/master/src/vdp_tile.c
- https://github.com/Stephane-D/SGDK/blob/master/inc/config.h
- https://github.com/Stephane-D/SGDK/blob/master/inc/vdp.h

## Precisely isolated R5 hypothesis

In original R3's `I_InitGraphicsHardwareSpecificCode` the
SGDK-heap-backed 2128-byte `r20_video_copy` buffer was allocated
BEFORE M3C's dual-bank boot diagnostic. The diagnostic then caused
SGDK to load and unload compressed font tiles several times.

In R5 *only with* `DOOM_R46_M3C_LATE_BUFFER` the exact same
`I_R21_AllocVideoCopy()` is called **after**
`R46_M3C_ShowVideoTest()` completes the 8x8 map/font restore,
and before R20 ever publishes a frame. The original
`R20_VBlankVideo` already tests `r20_video_ready==0` first.
No new global snapshot, no heap allocator changes, and no changes
to the 4x4 pixel banks are made.

All other builds, including R3, allocate exactly as before.
This is a boot-only diagnostic experiment: delaying the allocation
would NOT be a valid full gameplay 4x4 mode switch because the live
8x8 engine already needs the buffer.

## Four ROMs (controlled A/B)

- `doom-md-r46-primary-perf.bin`: 8x8 approved control,
  SHA-256 CI must equal `290677102bfb5a00b2a03f1150ba84204f903c51726ce78859a254128ac64c79`.
- `doom-md-r46-m3c-r3-safe-perf.bin`: known-good-source R3
  comparison, SHA-256 must equal
  `c6a397b19324feee32a1ec00d780daa8ed1088810459f0a13ed5d50e5090834f`.
- `doom-md-r46-r5-late-safe.bin`: same R3 SAFE pixels and VDP
  transitions, change R20 heap buffer allocation timing only.
- `doom-md-r46-r5-late-stress.bin`: the same R5 modification
  combined with 12 alternating bank phases.

The self-hosted runner additionally captures a read-only report of
the installed MarsDev SGDK `config.h` setting for
`LEGACY_FONT_LOCATION`; it does not modify the installed SDK.

## Acceptance gates

The new ROMs are **not automatically approved** when Actions turns
green. BlastEm headless CPU boot does not detect corrupt visible
fonts, invalid heap headers, or black-screen rendering.

For **each** R5 variant the user should observe all four color phases
(SAFE) or twelve phases (STRESS), visible R39f game afterward,
correct white characters in DEMO3 results, 2134 frames,
`ERRORS=0`, original-sized heap buffer header `2131`,
`RAW FREE` near the Primary baseline (~1386), and no crash.
Check more than one run; run one BlastEm instance at a time.

If R5 has **ERR=0 but font is corrupt**: address/font restore remains
broken; investigate font VRAM DMA backup and return semantics.
If R5 has **legible font but ERR=2**: the allocator corruption
precedes/occurs after delayed R20 allocation; add canary probes at
allocation, each map address setter, font reload, and each swap.
If R5 is **black or red**: use a no-font 4-bit RGB background stage
marker rather than `I_Error`, whose own text and heap might be broken.

## Permanent architecture proposal — NOT included in R5

Consider rebuilding a SEPARATE copy of `libmd.a` using
`LEGACY_FONT_LOCATION=0` consistently in the SGDK library,
header, linker and test build (do NOT change the shared MarsDev SDK
for all games). Font tiles would live at 16..111; user tiles start
at 112. The 798×2 visible dynamic tiles (25,536 bytes each)
can then fit under BG_A at E000 alongside static system/font
space if BG_B and Window are permanently relocated to safe
name tables, rather than being remapped while rendering.
The prototype VRAM index scheme (preserving 38 row-base gap)
would use bank0 dynamic 150..947, bank1 dynamic 986..1783.
Both must be checked for user game art / active planes collisions.

A VRAM-to-VRAM 3,072-byte temporary backup of the font is another
possible diagnostic technique, but requires care with SGDK's
implicit font reload and the occupied Window name table.
Do NOT blindly call `DMA_doVRamCopy` while a queued DMA or
hidden-bank upload is in progress.

Production rendering budget remains a separate blocker:
one full tile bank = 25,536 bytes plus 1,596-byte tilemap,
well beyond the nominal 7,200 bytes per NTSC VBlank. Updates
must be spread across frames with synchronized map presentation.

## Automatic research policy for major regressions

For severe black/red screens, corrupted graphics, memory integrity
failures or intermittent hardware corruption, pause feature work;
compare an approved control with exact hashes; inspect source +
release/version of the actual SGDK in MarsDev; check upstream source,
VDP documentation, SpritesMind and relevant forum reports; make one
controlled hypothesis test before resuming optimizations.
