# DOOM-MD R46 M3C R3 — Explicit SGDK font atlas restore

## Why R3 exists

User's BlastEm screenshot shows both R2 SAFE and R2 STRESS rendering
the DEMO3 results with colorful, corrupted letters; Primary, M2C and
the known-good M3B single-bank ROM display proper text. This is a
deterministic post-diagnostic corruption, not proven to be a crash.
**M3C remains unapproved** for real-hardware deployment.

## Root-cause hypothesis, verified address overlap

SGDK `TILE_FONT_INDEX` is a macro backed by *runtime* `maps_addr`.
With LEGACY_FONT_LOCATION=1, a 96-tile font, 32-byte patterns and the
original minimum map address `0xC000`:

- TILE_FONT_INDEX = (0xC000 / 32) − 96 = **1440**.
- Original glyph atlas = **0xB400..0xBFFF**, not 0xD400.
- M3C bank1 dynamic tiles **890..1687** = **0x6F40..0xD2FF**.
- Therefore bank1 *necessarily overwrites all 96 glyph patterns*.

When M3C mirrors BG_B/Window to E000, the SGDK repositions the font
to D400 (TILE_FONT_INDEX=1696), and on restoration the minimum map
address returns to C000. Changes to these addresses cause multiple
implicit calls to `VDP_loadDefaultFont(CPU)` via
`updateMapsAddress(FALSE)` and heap repacking.

The SGDK source explains the overlap, but we do not yet know why
implicit reload left the R2 font corrupted. The explicit restoration
experiment will test for a missed/deferred/failed implicit reload.
An SGDK decompression failure, DMA race, or other corruption may still
require separate investigation.

## Controlled comparisons: 8 ROMs

- Primary PERF; M2C PERF; M2C PLAY; approved M3B VIDEO.
- **R2 SAFE and R2 STRESS**, unchanged; both observed corrupted.
- **R3 SAFE and R3 STRESS**: identical to their R2 counterparts
  except for `DOOM_R46_M3C_FONT_RESTORE`.

R3 checks `VDP_MAPS_START == 0xC000` and `TILE_FONT_INDEX == 1440`
after resetting BG_B / Window and the original 8×8 tiles/CRAM.
It then **synchronously calls `VDP_loadDefaultFont(CPU)`**,
rejects a false return, and drains DMA before re-enabling video.
No permanent framebuffer, no renderer switch and no other gameplay
draw changes are introduced.

## Gates

- Source/address oracle proves B400..BFFF overlap and relative
  ordering of map, palette, font, and display transitions.
- All previous host tests continue to run.
- Compile 8 ROMs; check m68k symbols and feature flags; audit BSS,
  ROM metadata, and BlastEm boot smoke for each.
- User tests R3 SAFE first in BlastEm (several runs), looking for
  intact white text on results. Compare to R2 SAFE. If corrected,
  R3 STRESS tests long sequence and restore after 12 phases.
- If both still corrupt, STOP: investigate SGDK font loader status,
  compressed glyph data, transient `MEM_pack`, and VDP memory
  readback. Do not proceed to 4×4 gameplay.

Automated smoke cannot certify the glyph appearance. Real hardware
should only be used after the BlastEm font corruption is fixed.
