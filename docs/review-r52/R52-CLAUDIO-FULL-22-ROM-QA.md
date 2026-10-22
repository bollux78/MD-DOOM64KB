# R52 — Cláudio ColorMix full matrix (22 ROMs)

## Status and provenance
- Experimental branch: `r52-claudio-full-matrix`.
- Derived from earlier `r52-ab-colormix-matrix`, which remains as historical AB control.
- External generator: exact corrected Cláudio `gen_r52_ab.py` and `test_r52_ab.py`, imported under `scripts/lab/gen_r52_claudio.py` and `scripts/lab/test_r52_claudio.py`.
- Original hardware pistol deliberately disabled in all 22 ROMs, preventing the R51 gun/HUD artifacts from confounding color review.
- Generator is deterministic, requires NumPy and computes palette pairing offline for 14 PLAYPAL subpalettes. Frame-time code performs NO color-distance search.
- Main renderer retains Pair-V 76×44, the 3,344-byte buffer and 4×4 pixels. Plane A uses PAL0, plane B uses PAL1.
- Cláudio exports 224-word palette arrays, parity maps and composed `COLORMAP` LUTs, enabling comparison of lookup costs.

## Exact test variants
All 11 have paired `-play` and `-perf` ROMs, for 22 total:
1. `c0-vf`: original Pair-V Fast reference
2. `c1-cm50`: old 50/50 ColorMix + composed LUT
3. `old-n25`: first R52 static-seed near25 with index-zero repair
4. `old-l32`: first R52 static-seed luma32 with index-zero repair
5. `cl-n25-f`: Cláudio near25 zero-policy forbid, composed LUT
6. `cl-n25-a`: Cláudio near25 zero-policy allow, composed LUT
7. `cl-l32-f`: Cláudio luma32 forbid, composed LUT
8. `cl-l32-a`: Cláudio luma32 allow, composed LUT
9. `cl-free-f`: Cláudio free forbid, composed LUT
10. `cl-free-a`: Cláudio free allow, composed LUT
11. `cl-n25-df`: Cláudio near25 forbid with direct (noncomposed) lookup

For each variant, prepend `doom-md-r52-` and append `-perf.bin` or `-play.bin`.

## CI procedure
- Pinned VGM and shareware WAD preflight.
- R22 and R49 host oracles, with R22 isolated-compile fix for the new optional color mapping.
- Cláudio Python syntax, NumPy availability, baseline frozen tables, corrected `near25-forbid` structural oracle.
- Build each profile using unchanged R50 PLAY menu/benchmark/reset flags or R51-equivalent PERF flags.
- Audit BSS <=57,920 bytes, valid indices and Cláudio report/14 subpalettes, per-ROM manifest and SHA256.
- BlastEm boot smoke for 800 frames per ROM, archive all ROMs and reports.

## Caveats / manual inspection
- GitHub Actions success establishes build, memory and boot smoke only; NOT fidelity, frame alignment, correct gameplay HUD, stable shadows or improved FPS.
- When `allow`, index 0 means VDP transparency and may expose the backdrop; do not interpret it automatically as solid black.
- `forbid` prevents zero indices but will usually have different weighted chromatic error.
- Font/HUD currently use PAL0; if a light font becomes dark under a new PAL0 palette, isolate glyph colors or attribute palette in a separate corrective matrix.
- Pair-V A/B plane selection is 4-pixel column-interleaving, **not hardware alpha blending**.
- Run at least two comparable DEMO3 measurements per PERF at the same emulator settings and record median seconds/FPS. Expected historical reference ~5.31 FPS VF and ~5.03 FPS old ColorMix; those are NOT measurements of this batch.
- Compare identical E1M1 game tics on native no-filter RGB first, then composite/CRT; monitor red flashes, greens, near-black textures, HUD/title transitions and vertical stripes.
- Preserve older R50/R51 experimental branches; do not merge a color experiment before subjective and quantitative gameplay QA.

## Build failure that motivated this branch
The previous R52 run `39759453099` failed in `scripts/lab/test_r22_pixel4.py` because isolated host oracle did not define the new `R52_Map` macro. This matrix changes declarations to self-contained `r22_color` fallbacks before compile-time AB overrides and adds the Cláudio generator as its own path. Only the runner can establish that the issue is fully resolved.
