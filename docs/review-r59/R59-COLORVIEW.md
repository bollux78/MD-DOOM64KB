# R59 COLOR VIEW — H32/H40 + crop + dynamic A6 color modes

Experimental branch: `exp-r59-colorview-runtime` (forked from the successful R58 `exp-r58-cm6-viewmenu`).
The R58 source branch remains unchanged.

## Gameplay controls

From the OPTIONS menu, change **Color mode** with left/right:
- **CM6** (default): exact R58 ColorMatch output, approved baseline.
- **Balanced**: exact historical R57 `a6-balanced` palettes, pair books and color tables.
- **Tolerant**: exact historical R57 `a6-tolerant` palettes, pair books and color tables.
- **Accents**: exact historical R57 `a6-accents` palettes, pair books and color tables.

Video mode H40/H32 and H/V crop 0–32 px still use the original R58 runtime controls.

**Important:** Balanced/Tolerant/Accents use the actual R57 A6 CRAM palettes, not CM6 CRAM. Switching updates all mapping tables, 14 lighting/effect palettes and both Pair-V pattern banks together. Comparing should always be done with the same view/crop and scene.

## Implementation

- `gen_r59_colorview.py` generates R57 historical files using the pinned R57 generator; bundles all tables into a single ROM-resident header. No runtime optimization or RGB conversion.
- `r22_video.inc` selects precomputed wall, flat and composed COLORMAP lookup tables by profile, plus CRAM and paired pattern codebooks.
- In `R22_BeginFrame`, a requested switch waits for outstanding video work, temporarily disables display, replaces all 512 pair patterns and uploads palette 0 synchronously, then reenables display. Minor transition blanking is expected.
- No extra framebuffer, no heap allocation, no additional SRAM dependency.
- Default mode `CM6` preserves the approved R58 visual configuration.
- `test_r59_colorview.py` audits each generated historical table byte-for-byte, CM6 SHA256, mode wiring and the menu.
- Both PLAY and PERF builds are bundled; PERF automatically runs DEMO3, PLAY provides interactive comparison and the benchmark menu.

## Hardware test plan

1. Boot PLAY; verify no regression from R58 VIEW at default CM6.
2. Enter E1M1, stand still and open Options, switch among CM6/Balanced/Tolerant/Accents. Watch for corrupted colors, persistent glitches or crashes on first transition.
3. Repeat in both H32 and H40, with crop 0/16/32.
4. Check opening/closing menu with START, game over, resets, transitions and palette effects (red damage flash, etc).
5. Compare PERF DEMO3 against R58 with BlastEm divider 7 and divider 4, using same environment. Actual hardware tests remain required.

## Build

GitHub Actions: `.github/workflows/r59-colorview.yml`, artifact name `doom-md-r59-colorview-play-perf`.

No R57 A5 code is included. Do not merge into release before real-hardware validation.
