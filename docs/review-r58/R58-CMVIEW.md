# R58 CMVIEW: ColorMatch CM6 + dynamic H40/H32 + independent crop

**Goal:** one PLAY ROM with the ColorMatch CM6 palette that performed well
on the user's television, plus Werk's complete dynamic screen configuration
under Options. PERF companion for reproducible comparisons.

## Source contracts

- Video/backend: `r57-runtime-view-menu-lab` (latest successful Werk menu).
- Palette/codebook: `exp-r57-colormatch-prepared`, generator copied verbatim
  to `scripts/lab/gen_r57_colormatch.py`. Uses exactly the same R56 A6
  palette snapshot before ColorMatch conversion as the successful CM6 build.
- Existing 4x4 Pair-V renderer, R50 fast Start menu, BGM, SFX, static art,
  player physics and 35-Hz game logic are unchanged.
- Source framebuffer remains 76x44 packed samples (4-bit codes).
- Options: H40/H32; H/V crop independent 0/8/16/24/32 pixels **per edge**;
  changing settings does not restart E1M1.
- Title, intermission and options UI stay H40; gameplay can use H32.
- Default H40 with H/V crop=16: 264x136 gameplay. Full H40 with 0/0:
  296x168; H32 with 0/16: 256x136; H32 with 16/16: 224x136.
- No SRAM storage for video settings yet.

## PCM/VRAM/graphics safeguards

Palette generation changes offline tables only. The H32/H40 implementation
retires pending DMA before mode/geometry changes, clears planes and Window,
restores horizontal scroll and HUD, and clips walls/flats/sprites and Pair-V
DMA to the selected rectangle. No per-frame optimization is assumed.
The original Pair-V title screens, DMA protocol, music and cache are retained.

## Approved CM6 identity checks (normal PLAYPAL)

- `unique_cram_words_union_normal=24`.
- `shared_free_color_source_slots=0`.
- `mixed_code_count_per_plane=[2,3]`.
- Exact ordered palette slots from original approved CM6 run:
  PAL0 [41,11,43,7,2,1,32,52,10];
  PAL1 [8,22,39,16,15,35,19,40,36].
- Report plus headers must match between PLAY and PERF.
- Six shared solid flat anchors; both 34x256 composed COLORMAP LUTs.

## Builds

- `doom-md-r58-cmview-play.bin`: gameplay, fast START menu, built-in
  Benchmark, video/crop Options, ColorMatch.
- `doom-md-r58-cmview-perf.bin`: same ColorMatch and default H40 16/16,
  automatic DEMO3 timedemo comparator.

## Required gates

Fish syntax, pinned shareware WAD/VGM, SGDK/MarsDev, color generator,
R56 LUT oracle, Werk's 50-geometry + mode transitions host oracles,
<=4MiB ROM, <=57,920 B BSS, ROM name/header, PLAY/PERF palette identity,
BlastEm PERF 800 and 30,000 frames. These are regression checks only.
Gameplay/menu/H32 display resynchronization and FPS need manual hardware
testing, especially on a television.

## Comparison procedure

Test ColorMatch CM6 (R57) vs R58 CMVIEW at matching H40 dimensions
(choose H crop 0 V crop 0 in R58), then compare H40 vs H32 and incremental
crop. Check both appearance (gray ceilings, blue floor, brown walls, red/green
technical panel) and real FPS/timedemo, Start > Options transitions, weapon,
HUD, automap, next level, toggling modes several times.
