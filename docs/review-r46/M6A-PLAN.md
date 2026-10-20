# DOOM-MD R46 M6A — audited VRAM layout, no pixel-mode switch yet

## Proven base and approval

User hardware-tested **R46 M3C R5 SAFE and STRESS**, both with legible
final text, 2134 DEMO3 frames, R28 ERRORS=0, raw free near 1384,
and no crash. Preserve R5 EXACT source and binary SHA-256:

- Primary: `290677102bfb5a00b2a03f1150ba84204f903c51726ce78859a254128ac64c79`
- R5 SAFE: `e5b9363f0327bb4624acb0efa1bc4b391cd7b1a71252587b12cba6b2c42b5766`
- R5 STRESS: `d2f6ecb81a187056699ff7c2bc362b5b1a37205797dcaa604264d1c46944ced6`

Do NOT base R6 on R4/R4B (black/red screens and possible heap corruption).
M6A compiles a **metadata-only validation** and does not use new tile
indices to drive VRAM. New `r6a-audit-*` builds still use precisely the
proven R5 video paths and SGDK as hardware controls.

## Crucial correction to earlier proposed compact tile layout

The native R22/M1B/M3A pipeline reserves 836 tile index slots per
physical bank, with a **38-tile row offset** and 798 actual dynamic
pattern tiles. Reducing the bank step to 798 without a coordinated
packer change would overlap the static solid-tile reserved area and
violate bank address invariants. M6A preserves **836**.

Fixed font contract (requires a new isolated libmd.a, not yet built):
- SGDK 16 immutable system tiles index 0..15: 0000..01FF.
- 96 fixed-font glyph tiles index 16..111: 0200..0DFF.
- New `TILE_USER_INDEX=112`. Existing R39f 8x8 static patterns
  start here; all compiled C-generated colormap LUTs already use
  `SOLID_TILE_INDEX + tile` and will follow `TILE_USER_INDEX` when
  consistently rebuilt with that compiler/library ABI.
- Reserved bank0 index 112..149, including 8x8 solids and top-row
  mapping indices (not all can be used for other artwork).
- Bank0 dynamic patterns 150..947 (798 tiles): VRAM 12C0..767F.
- Bank1 reserved index 948..985.
- Bank1 dynamic patterns 986..1783 (798 tiles): VRAM 7B40..DEFF.
- Remaining 8 tiles (=256 bytes) DF00..DFFF.
- BG_A name table E000..EFFF (4,096 bytes, 64×32).
- HScroll F000..F3FF; SAT F400..F7FF; remaining F800..FFFF.

During future 4x4 mode BG_B and H40 WINDOW hardware map addresses
must both alias safe E000, while only BG_A is actively written. This
preserves font and name table patterns but **does not** create a second
independent tilemap, and bank map flip is not yet atomic. BG_B / Window
must be disabled or carefully controlled while aliasing a live name
table, and their original maps must be rebuilt before returning 8x8.

## SGDK / MarsDev ABI compatibility findings

MarsDev source `andwn/marsdev/sgdk/Makefile` pins SGDK revision
`cb114acadc454440fcddd616d9a7dd5a693b1b13` unless overridden.
The pinned SGDK version's `inc/vdp.h` defines
`TILE_USER_INDEX=16`, `TILE_FONT_INDEX=TILE_MAX_NUM-FONT_LEN`.
The modern `LEGACY_FONT_LOCATION=0` toggle is **absent** at this
pinned revision; the user's installed `config.h` indeed lacked it.

Implement M6B in an isolated copy of that EXACT SGDK revision with a
matching library **and** public headers and a controlled build:
- `TILE_FONT_INDEX=16`, `TILE_USER_INDEX=112`
- `TILE_SPRITE_INDEX=TILE_MAX_NUM-spriteVramSize`
- Adjust old `src/sprite_eng.c` (`SPR_initEx` uses
  `index=TILE_FONT_INDEX-size`; invalid when font fixed) to use
  `index=TILE_MAX_NUM-size`; verify sprite engine is not initialized
  by the current Doom port.
- In `src/vdp.c`, `updateMapsAddress(FALSE)` reloads font and
  `MEM_pack()` unconditionally when min map changes; modify it only
  for this isolated fixed-font library so it does NOT decompress font
  again solely because map base changes when font remains at tile16.
  R20's heap snapshot remains delayed until after the M3C diagnostics
  in this initial prototype; runtime switching needs an independent
  ownership protocol.
- Build from **copy** of pinned revision, not the shared
  `~/mars/m68k-elf` installation. `DOOM_MD_GDK` already exists in
  `scripts/build_silent.fish` to point to an isolated SDK copy.

The current M3C boot diagnostic and M1B/M3A oracles still assert
the legacy bank0 54..851 and bank1 890..1687. **Do not swap library
without updating all of these packer constants and existing tests
behind an isolated M6B feature flag.** Unlike M6B, M6A links only
a metadata function, and cannot corrupt the video.

## DMA timing and future renderer

Each bank upload requires 798×32 = 25,536 bytes; 38×21×2 = 1,596
tilemap bytes; total 27,132. At 7200 bytes nominal per NTSC VBlank,
a complete transfer takes **at least 4 VBlanks**, excluding overhead.
The current R5 CPU upload may blank video and is not a streaming
60Hz renderer. A future M6D needs bounded DMA chunks, queued buffer
lifetime guarantees and atomic map commit after the hidden bank is
complete.

## R6A gates and deliverables

- Host C oracle `scripts/lab/test_r46_m6a_layout.c` exhaustively
  enumerates every dynamic tile and checks collisions.
- Python oracle compiles host C, exhaustively calculates all indices
  and audits the opt-in build flag.
- M68k binary with M6A gate checks ONLY the prospective metadata
  before running proven R5 SAFE/STRESS video.
- CI builds/verifies Primary, bit-identical R5 SAFE/STRESS and optional
  M6A SAFE/STRESS. Tests ROM size, flags, BSS and BlastEm boot.
- No M6A user physical-hardware test is required until M6B switches
  the REAL graphics layout. M6A ROM display should look exactly R5.

## Automatic incident response

Any future black/red screen, graphics corruption or heap R28 ERRORS
>0: stop new features, compare proven hashes, inspect pinned library
source + release, then search SGDK VDP docs, SpritesMind and the actual
toolchain's build options before proposing a one-factor reproduction.
