# R39f — CRT-oriented vertical dither (8x8 native cell renderer)

**Purpose:** direct CRT comparison in the *same game scene* of three 8x8 tile patterns: **Off**, **Checker** and **Vertical**. This is separate from the future 8x8/4x4 runtime integration. The authentic 4x4 R40b render path has not been changed.

## Base / no regression policy

Branch `r39f-dither3-vertical` forked from `r39e-audio-toggles` (the approved **38x22 cell gameplay** renderer), with the proven R39c **mall** MOVEP SRAM cache+map optimizations, R39d ROM dither toggle, independent R39e Music/SFX controls, R30 Bayer8 static title/intermission, 52 mixed PCM sound effects, multi-track XGM2, same maps and projection. The user approved the R40b native 4x4 static text anti-flicker fix separately; the R39f branch deliberately does not change the 4x4 path.

**R39e reference:** DEMO3 2134 frames at stock NTSC CPU, **11.80 FPS**, 180.78–180.82 sec. Compare both R39f PERF ROMs under the same BlastEm setup and no overclock. No speedup is promised.

## User UI (PLAY)

Options > **Dithering** displays **Off**, **Checker**, or **Vertical**. The A/Enter action cycles the value:

`Off -> Checker -> Vertical -> Off`

Default at power-up: **Checker**. State carries through the levels in the current session. Music and SFX each remain independently switchable and default to ON. Dithering changes 3D textures, sprites, and flats; original full-resolution title/intermission images and CRAM palletes remain untouched. Color choices are identical between checker and vertical, only the eight rows in each *mixed-color tile* differ.

- `Off` uses the existing R39d solid mapping (tile word bank 0..15).
- `Checker` uses the exact original R35d 50/50 checker mapping (mixed tiles 16..120).
- `Vertical` uses the same 50/50 pair mapping shifted by 105 tile indices (mixed tiles 121..225), with `ABABABAB` **on all eight horizontal rows**.
- The palette bank and original color-pair selection do not change; new precomputed ROM colormaps are selected by pointer at menu input. The cached wall colormap is invalidated on selection. No per-pixel dithering runtime calculations and no extra work RAM.
- These are **vertical color stripes one native pixel wide within each 8x8 VDP tile**, not changes to the 3D sampling resolution. On an LCD they may look less attractive than on a CRT.
- Extra fixed VRAM: 105 tiles ×32 bytes = 3360 bytes. Tiles are installed on initialization and restored after native static art is exited. No extra tile uploads per 3D frame.

## ROM set

1. `doom-md-r39f-control-cell-perf.bin`: R39e baseline: Checker/Off only, audio toggles ON, MOVEP mall, DEMO3.
2. `doom-md-r39f-dither3-cell-perf.bin`: Same DEMO3, tri-state code compiled, starts in Checker; should preserve the baseline.
3. `doom-md-r39f-dither3-cell-play.bin`: Full playable with CRT checker/vertical A/B selection, Music, SFX.

Both timedemos must run all 2134 DEMO3 frames on standard 68000 timing. Build should fit the linear 4MiB ROM with the same SRAM gating, not require a new cartridge mapper. The workflow produces `R39F-CRT-VERTICAL-3ROMS.zip` within the GitHub Actions artifact and also the separate BINs, LUT snapshots, build logs, and `R39F-MANIFEST.json`.

## Validation

- Before linking, generator produces `doom_colormap_cells[32][256]` and `r39d_colormap_cells_solid[32][256]` **unchanged** from the R39e control build. `scripts/lab/test_r39f_vertical.py` checks all 8192 shade slots and 256 color slots, their palette banks, vertical tile offsets, and all 105 possible ABAB row patterns. It asserts exactly 169 mixed colors in the palette (the R35d count).
- GitHub CI audits each ROM's compile flags, real size, header/end address, dither report, and then boots 300 frames in BlastEm. **A headless boot does not prove visual correctness**; the CRT and full timedemo are manual checks.
- CRT: open the same E1M1 wall, same viewing angle and camera position, cycle modes; compare flicker/shimmer while moving sideways and rotating; inspect walls, gradients, floors, ceiling, weapon and sprites. Test options and Music/SFX while changing modes, then exit/reopen menus. No stale cells or palette changes.
- Record DEMO3 mean/min/max FPS, elapsed time and 2134 frames for both PERF ROMs. If the new code is within measurement noise, keep the runtime switch as an option; otherwise profile.

## Key implementation files
- `scripts/gen_colormap_cells.py`: R39f third ROM color/colormap mapping based strictly on existing R35d pairs.
- `src/i_genesisv.c`: 105 new vertical pattern tiles and 3-state pointer selection and colormap memo invalidation.
- `src/r39f_dither.h`: mode API.
- `src/m_text.c`: Options cycling and labels.
- `scripts/lab/build_r35_linear.fish`: opt-in compile flag `DOOM_R39F_DITHER3=1`, dedicated build ID.
- `scripts/set_rom_identity.py`: R39f 4MiB linear cartridge identity.
- `.github/workflows/r39f-crt-vertical.yml`: builds control, tri-perf and tri-play, audits and 300-frame boot smoke.

**Do not merge into the live R40 4x4 branch until validated.** R40b pixel4 native-art anti-flicker correction is already separate and requires its own validation/merge.
