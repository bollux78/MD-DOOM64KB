# R51 — Hardware first-person pistol/hand sprite experiment

## State and baseline

Branch: `r51-hw-weapon-sprite` from **validated** R50 `r50-native-menu-mask-fix`. The R50 user explicitly confirmed menu redraw, soft reset, PLAY benchmark, menu freeze and New Game work. Do not alter that branch.

R51 Actions run: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39711932873  
Four-ROM artifact: `doom-md-r51-hw-weapon-sprite` (CI passed).

## Motivation

The source Doom port renders the first-person weapon in `R_DrawPSprite()` at the end of `R_DrawMasked()`, using the same software masked columns and the Pair-V 76×44 viewport as the world. The experiment removes that raster cost **only for PISG pistol/hand frames**, displaying instead actual 68000 Mega Drive VDP hardware sprites driven by SAT at VRAM `0xF400`, with new artwork in spare VRAM tiles **16..255** (untouched Pair-V tiles begin at 256; font at 1440).

All other weapons, world sprites, masked walls, flash and invisibility remain software-rendered in the control flow. Unsupported frames use an exact software fallback.

## Source and artwork conversion

`scripts/lab/gen_r51_hw_weapon.py` reads the **same episode-converted Doom64KB WAD as the PLAY ROM**, decodes Big-Endian Doom patch columns, extracts original PISG picture pixels with transparent areas, scales to approximately native physical size (304/320 horizontally, 220/200 vertically), quantizes an optimized 15-color opaque PAL2 and packs column-major VDP 8×8 patterns for a 32×32 hardware-sprite mosaic.

CI verified these five WAD frames:

| Patch | Output physical pixels | VRAM tile patterns | Hardware sprites |
|---|---:|---:|---:|
| PISGA0 | 54×68 | 63 | 6 |
| PISGB0 | 75×90 | 120 | 9 |
| PISGC0 | 63×89 | 96 | 6 |
| PISGD0 | 58×89 | 96 | 6 |
| PISGE0 | 74×113 | 150 | 12 |

The first-person weapon moves via **sprite SAT XY updates**; pattern tiles reload only on weapon frame changes or after native static art overwrites the shared VRAM atlas. ColorMatch/ColorMix PAL1 and scene PAL0 are not altered. The weapon uses hardware palette2, with 15 distinct opaque CRAM colors.

## Memory and automatic checks

- R51 PLAY software baseline: **57,880 B BSS**
- R51 PLAY with hardware pistol: **57,884 B BSS** (+4 bytes)
- Same BSS for ColorMix+weapon: **57,884 B**
- All four ROMs pass compilation, generator oracle, 800-frame BlastEm smoke and 57,920 B boot guard.
- **No benchmark FPS or visual equivalence is claimed yet.** Automated smoke does not interact with the weapon or verify the hardware sprites' actual on-screen placement.

## User ROM A/B tests

1. `doom-md-r51-vf-ctrl-play.bin`: fully software-rendered gun reference.
2. `doom-md-r51-vf-hw-play.bin`: first-person PISG hardware sprite, plain Pair-V.
3. `doom-md-r51-cm50l-hw-play.bin`: same sprite with ColorMix 50/50 + composed LUT for the world.
4. `doom-md-r51-vf-ctrl-perf.bin`: untouched PERF control.

Verify pistol visibility and sharpness at title->E1M1, alignment during turning and weapon bob, flash fallback while firing, switching to other weapons, status-bar clipping/occlusion, titles and menus, reloading after returning from native title, soft reset, repeated integrated DEMO3 and actual FPS.

## Next: hardware sprite expansion

If this pilot works, investigate all weapon frames and their flash overlays with a shared, optimized ROM palette2 and a sprite-atlas management policy. For art wider than 240 tiles, measure selective crop, progressive atlas/palette switching, or more VRAM without overwriting Pair-V and fonts. Preserve no-heap and WRAM constraints. Account for 20 per-line / 80 total hardware sprites and non-tile-aligned Y/HUD clipping; never infer that all weapons automatically fit.

## ColorMix V2 independent workstream

User reports the current ColorMix **rarely appears to mix** and mostly produces additional orange tones, although some detail becomes newly visible. Current generator selects 15 PAL1 slots without excluding duplicates against PAL0 and only one P1 partner *pair per 16 PAL0 classes*. Its 8% + absolute error threshold and matching upper/lower 4px gating severely limit coverage. Do not declare success solely because PAL1 contains 15 slots.

Plan separately:

- Measure distinct PAL1-vs-PAL0 CRAM entries for all 14 Doom subpalettes and count actual eligibility across source/colormap and rendered DEMO3.
- Weighted source-color histograms over actual rendered scene (not 256 uniform Doom indices), including grey, brown, green and neutral colors rather than orange-dominant choices.
- Test a palette-selection objective balancing fidelity gain, chromatic diversity and coverage, excluding duplicates against PAL0.
- Vary gate thresholds and distinguish spatial dithering (opaque pixels) from false alpha-blending claims.
- Consider full multicolor sprites with PAL2 as a *separate* visual change, never conflate with world ColorMix.
- Keep FPS benchmark comparisons to Pair-V Fast stable baseline (5.30 PLAY, 5.31 PERF); no promised performance uplift.

**Decision:** Pair-H remains only historical one-ROM reference, not in regular matrices.
