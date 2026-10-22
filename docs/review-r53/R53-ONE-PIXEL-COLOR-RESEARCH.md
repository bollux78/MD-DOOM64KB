# R53 research — 1-pixel microdithering without 4-pixel stripe artifacts

Date: 2026-10-22. Source: user R52 screenshot of 11 simultaneous PLAY ROMs and DEMO3 benchmark comparisons. Experimental branch `r53-microdither-research`, based on green `r52-claudio-full-matrix` (SHA `9c3f649...`). **Design only, not implemented or compiled.**

## User-validated R52 evidence

- User reports every R52 ROM boots and plays correctly. Three visually preferred screenshots have handwritten red underlines: first row, second and fifth windows; second row, fifth window. Window title bars are truncated, so do **not** claim exact binary filenames for these three until their names are provided.
- Native RGB/BlastEm screenshot shows intrusive vertical 4-physical-pixel stripes, particularly on texture walls, rails, broad surfaces and edges.
- DEMO3 at 2,134 frames: VF baseline **5.31 FPS / 401.93 s**; R49 CM50L **5.03 FPS / 424.42 s**; original frozen R52 dual palette **5.25 FPS / 406.33 s**; Cláudio R52 composed-LUT variants **5.46 FPS / 390.87 s**; Cláudio `n25-df` noncomposed LUT **5.25 FPS / 406.33 s**. Results photographed, not independently rerun.
- New throughput win: +2.82% FPS vs VF, +8.55% vs R49 ColorMix. Preserve that if possible.

## Hardware and renderer geometry

- VDP: each 8×8 tile's *attribute word* selects one palette (not per pixel); the 4-bit pixel value chooses a color inside the selected 16-entry palette, where index 0 is transparent.
- Pair-V raster currently 76×44 logical 4×4 samples. PAL0 lives on Plane A (even logical columns), PAL1 on Plane B (odd logical columns). Plane B is shifted +4 physical pixels horizontally.
- A and B **do not carry two representations of the same 4×4 sample**; they carry neighboring source columns. Therefore, narrowing their transparent masks to alternate every physical pixel would mix DIFFERENT source samples, erode boundaries and contaminate flat/wall edges. **Do not attempt this as a drop-in tile-pattern-only change.**
- Each current 8×8 tile encodes a *vertical* pair of four-pixel-high samples (two 4-bit indices). Static 256-pattern bank supports all 16×16 vertical pairs; the 3,344-byte WRAM framebuffer stores 38 A tile words and 38 B tile words per 8px-tall row.
- True PAL0/PAL1 alternate pixels within a *single* logical 4×4 sample requires both color indices for that same sample to be available to two planes at that physical location, with appropriate mask and duplicated/repacked tile descriptors. A naïve 8×8 tile encoding of both adjacent 4×4 columns and both vertical samples has 16^4 combinations before including pattern choices: impractical as a static VRAM bank. Requires design research for compact representation, dynamic tiles, or another architecture.
- Do not use whole-scene 8×8 dynamic tile uploads without an explicit VRAM-bandwidth and cycle budget (at least hundreds of patterns per frame, potentially tens of KiB vs today's tiny name-table DMA).

## Candidate A: cheap 1px microdither **within each plane palette**

This uses two existing opaque colors from **PAL0** in A and two from **PAL1** in B, NOT cross-palette PAL0+PAL1 within one logical pixel. It may reduce visible 4px bands and create more intermediate tones but cannot by itself remove the 4px AB seam. Label output accurately.

- Generate a deterministic companion-color LUT `partner[2][16]` offline (all entries 1..15) based on *actual* Cláudio `r52_even/odd`, CRAM0/1 and PLAYPAL normal palette. Optimize per base palette entry. Penalty for large ΔE and huge luma contrast; choose companion = base when mixing has no measurable benefit.
- Build new immutable A-pattern bank 256..511 and B-pattern bank 512..767. Existing font starts at tile1440. No new gameplay framebuffer; no per-pixel work in the 68000.
- In `R47_ClearPairBuffer` for experimental R53 only: A word starts 0x0100; B word starts 0x2200 (PAL1 + pattern base512), retaining bits on subsequent writes.
- In `R47_LoadPairTiles`, precreate A and B 256 tile patterns, instead of sharing one solid tile across both planes. Rows 0..3 of each tile encode upper logical sample; rows 4..7 encode lower. Only its physical 4px coverage may be opaque. Avoid 0 in opaque nibble.
- Compare these subpatterns within each 4×4 logical sample:
  - `M25`: 1 companion pixel + 3 base pixels per row; shift companion x offset on successive scanlines (a 4×4 dispersion). Microdither is one physical pixel.
  - `M50`: 2 base + 2 companion pixels in 1×1 checkerboard.
  - `SOLID`: current 4px uniform cell, unchanged control.
- Both A/B still render 4px *logical* samples; 1px is the **dither pattern's physical pitch**, not new geometry resolution.
- Do not promise higher FPS; initialization uploads 256 extra patterns, but gameplay fast LUT and name-table DMA should remain the same. Measure cold-start and actual DEMO3.

## Candidate B: jointly reoptimize Cláudio's palettes for LCD/RGB output

- Existing `near25`, `luma32`, `free` optimize average color errors; a 4px band could be undesirable even when the averages are good.
- Add spatial alias/contrast penalty measured after physically accurate 4px column rasterization, evaluated separately for *unfiltered RGB* and composite/CRT simulations.
- Try tighter pair separation and per-scene histogram to push the two plane colors closer where edges or high-frequency patterns dominate.
- Since per-scene weights and TV filtering change the optimum, use multiple holdout frames E1M1 + E1M2/E1M3 before promoting. Prioritize the three visually preferred screenshot profiles once their binary names are known.

## Candidate C: true 1px cross-palette mix (research only)

- Derive a new representation where BOTH A and B have access to the relevant logical pixel's own two palette indices; verify sample mapping, fixed VRAM tile bank count, tilemap attribute budget, 21×38 DMA row layout, boundaries and HUD.
- Investigate constrained cached tile dictionaries, scanline-structured tiles or hybrid spatial allocation before dynamic bitmap VRAM uploads; calculate number of tile patterns, worst-case DMA bytes and 68000 cycles. No 60Hz/H-INT palette switching at 1px (physically not 1 pixel granularity).
- Gate by image fidelity, not just apparent extra shades. This solution is considerably more invasive than Candidate A.

## ROM QA recommendation

Hold existing `r52-claudio-full-matrix` intact. First test RGB TV output of the three visually preferred ROMs and record exact filenames. Then compare SOLID/M25/M50 for the preferred `near25` and `free` variants (both index-zero modes as needed), each in PLAY+PERF. Keep same 2,134 DEMO3 tic count, two timedemo runs each, native pixel screenshot at the same camera, and CRT/TV photo. Watch shimmer, moire, checkerboard, edge bleeding, dark gradients, red damage flashes, menus and the HUD.

Acceptance: less intrusive perceived vertical 4px striping at native physical size; correct geometry and sprite outlines, no unexpected transparent pixels; ≥ current measured 5.46 FPS preferred (acceptable regression must be justified by clear visual advantage). If microdither does not remove stripe seams, redirect work to Candidate B before attempting costly C.

## R52 CRT-simulation visual checkpoint (user review, 22 Oct)

- User compared all 11 PLAY windows against an overlay of the original game's frame, using a CRT simulation.
- **Finalists: top row, column 2 and top row, column 5**; both marked with red strokes below the viewport/HUD.
- The original image's beige/brown pillar, neutral-grey background, saturated dark-blue floor and warm architectural accents are the visual anchors. The large differences in geometry/texture are expected from the 76×44 logical resolution; do not score them as pure palette error.
- Compared to the other R52 samples, the two finalists preserve more plausible warm/neutral balance, without the strong magenta/red or olive tint of some alternatives. The CRT filter softens the 4-pixel banding but does not prove it disappears on real television output.
- **Exact ROM filenames are not recoverable from this montage** because title bars are elided. Do not guess file identity from screenshot order; confirm the binary names before targeted R53 compilation or lock them from a reproducible screenshot manifest.
- Keep both finalists and the `c0-vf` reference. Candidate A microdither can be evaluated at 1-pixel spatial pitch INSIDE each 4×4 cell, while preserving 4×4 scene sampling. For accurate cross-PAL0/PAL1 blending in the same cell, see Candidate C and its structural constraints.
- Require real CRT/TV captures plus native unfiltered captures before promotion. Screenshots from software simulation are useful as a ranking criterion, not hardware verification.
