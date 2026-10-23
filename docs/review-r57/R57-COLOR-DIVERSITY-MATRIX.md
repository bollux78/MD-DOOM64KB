# R57 — fixed R55 palettes, balanced training and wall-pair tolerance

Base: R56 `a64758c342e4f5565b9dbc06bb0db1daca19044f`.
Authorized by Daniel on 2026-10-23 after R56 colour-diversity regression review.

This matrix changes offline tables only. The R56 Pair-V renderer, 3,344-byte
framebuffer, pattern layout, fast START menu, music and SRAM code remain unchanged.
All new experimental profiles freeze the complete 14-effect R55 A4/A6 CRAM and
flat LUTs. The compiled R56 snapshot is a separate control and uses its own palettes.

## ROMs

Each profile has PLAY and PERF. Prefix `doom-md-r57-`, suffix `-play.bin` or `-perf.bin`.

| Profile | Purpose |
| --- | --- |
| `legacy8` | Existing cell/8x8 backend control; not a colour-optimizer experiment |
| `c55-a6` | Exact R55 A6 colours/maps in the R56 renderer using solid `(i,i)` pairs |
| `c56-a6` | Byte-exact current Cláudio R56 A6 table snapshot, regression reference |
| `a6-fixed` | H1 pair selection with frozen R55 A6 CRAM, original frequency weights |
| `a6-balanced` | Same, with 50% frequency + 50% equal nonempty hue/light bins |
| `a6-tolerant` | Balanced, allowing wall-pair A/B RMS Lab separation up to 8 before penalty |
| `a6-accents` | Tolerant plus one reserved red and one reserved green pair code per plane |
| `a4-tolerant` | Tolerant policy on frozen R55 A4 palettes/anchors |
| `a4-accents` | A4 tolerant with red/green pair reserves |

Total: 18 ROMs, with ELF, flags, BSS audit, palette headers, SHA256 manifest and
offline optimization report. No VGM, XGM2, gameplay-tick or renderer changes.

Compare `c55-a6` vs `a6-fixed` for the new pair selector with fixed palettes;
`a6-fixed` vs `a6-balanced` for weights; `a6-balanced` vs `a6-tolerant` for the
wall tolerance; `a6-tolerant` vs `a6-accents` for rare-colour reserves.
A4 vs A6 also changes the R55 source palette, so it is a system-level comparison,
not an isolated two-code increase. The H1/H2 study was not the previously compiled
Cláudio snapshot; R57 versions its own exact selector for reproducibility.

## Objective and constraints

Greedy codebook initialization plus alternating assignment/refinement, with 15
opaque pair codes per plane and fixed solid shared flat codes 1..K. H1 evaluates
CIELAB76 errors of 50/50 linear-sRGB pair means against each source PLAYPAL colour,
including chroma undershoot, endpoint hue/contrast penalties, and coupling of the
same target between planes. Normal effect has 75% weight, other 13 share 25%.
Codebooks are refined with a non-increasing objective. See generator for exact terms.

Original training proxy: wall patches, COLORMAP levels 6..22, 35% uniform coverage.
Balanced weighting uses seven hue sectors plus neutral (C*<20) and three L* bands
at 25/50; empty bins receive no mass, within-bin source frequencies are retained.
At this base, dark mass changes 71.65% -> 52.49%, chromatic mass 17.87% -> 50.60%.
These are optimizer training weights, not proportions of pixels shown in a game.

Wall tolerance uses a hinge on RMS Lab difference between effective A/B pair means
across effects. Flats remain exactly equal and solid, regardless of that tolerance.
Accent profiles lock two additional free pair codes around Lab hue40/red and
hue140/green; they do not allocate new VRAM or framebuffer bits. This is a deliberate
tradeoff: extra accent coverage may reduce tonal precision elsewhere.

The model is not a calibrated CRT/composite simulation, and no metric proves visual
improvement. Do not force every pair to mix: solids remain legal and often preferable.

## Checks

Local host: complete R56 table oracle, frozen R55 CRAM and flat LUTs across 14 effects,
exact R56 control hash, exact R55 colour reproduction for all indices/parities/effects,
monotonic optimization, and compilation/execution of the real R56 C pattern-row helper
over all 256 upper/lower pair combinations in both planes.

Runner: fish syntax, existing preflights, SGDK/MarsDev builds, per-ROM BSS <=57,920,
header equality at build time, size <=4MiB, ROM/ELF/flags/SHA256 manifest. PERF-only
BlastEm checks at 800 and 6,000 emulated frames are process/boot regressions; they do
not complete the ~390-second DEMO3 or measure in-game FPS. PLAY remains manual.

## Local/runner commands (fish)

```fish
python3 scripts/lab/gen_r57_diversity.py --repo . --out dist/r57-diversity/tables
python3 scripts/lab/test_r57_diversity.py --repo . --tables dist/r57-diversity/tables --host-c
# After existing VGM/WAD/toolchain preflights:
set -gx DOOM_R20_BGM_VGM (realpath res/e1m1.vgm)
python3 scripts/lab/build_r57_matrix.py
```

Compare the same camera/tic in E1M1 and additional E1M2/E1M3 scenes. Check ceiling,
floor, beige pillar, coloured technical panels, shadows, HUD/gun, damage flashes,
menu START, title return, map transitions and sound. Quantify real timedemo by total
seconds and 2,134 frames, not the corner FPS or headless host wall time.

Start visual review with c55-a6, c56-a6, a6-balanced, a6-tolerant, a6-accents.
Higher hue coverage is not automatically more faithful; protect against false
rainbow hues, coarse phase bars, washed detail and crushed shadows.
