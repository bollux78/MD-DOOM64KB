# MD-DOOM R49 — Pair-V native-art cleanup and conservative ColorMix

Date: 2026-10-21. Experimental development branch: `r49-v-colormix-fixes`.

## Reference and intent

- R47 Pair-H ALL baseline: **4.71 FPS / 453.22 s**, DEMO3 NTSC.
- R48 Pair-V Fast ALL measured: **5.31 FPS / 402.23 s**, DEMO3 NTSC.
- All R49 ROM results are unknown until measured; do not promote before hardware and PLAY checks.
- Fix the native TITLEPIC remnants behind HUD and left/right borders in PLAY.
- Remove residual Pair graphics behind PERF results.
- Compare optional composed LUT.
- Test ColorMix **without forcing dithering at the expense of color accuracy**.

## ROM matrix

| ID | Source flags | Mode |
|---|---|---|
| h-all | Pair-H ALL | PLAY + PERF |
| vf-all | Pair-V Fast ALL | PLAY + PERF |
| vlut | Pair-V Fast + ROM composed COLORMAP | PLAY + PERF |
| cm50 | Pair-V Fast + PAL1 + 2:2 gated mix | PLAY + PERF |
| cm50l | cm50 + composed LUT | PLAY + PERF |
| cm75a | Pair-V Fast + PAL1 + 3:1 gated mix | PLAY + PERF |
| cm75b | Pair-V Fast + PAL1 + 1:3 gated mix | PLAY + PERF |
| v-raw | Pair-V ordinary (non-Fast) | PERF only |

Total: **15 ROMs**. `*.bin`, `flags-*.txt`, `size-*.txt`,
`COLORMIX-PALETTE-REPORT.json`, host-oracle reports and BSS audit in one artifact.

## VDP hardware constraints

- Plane A and B do **not** perform per-pixel alpha blending.
- Each tilemap word selects one shared 16-entry CRAM palette for that tile.
- Pair-V uses Plane A/B with complementary 4px regions and HScroll(B)=+4.
- Existing Pair-V 3344-byte framebuffer is retained, and VBlank still DMA-copies tilemap words.
- ColorMix requires no new bitmap or pixel cache in WRAM.

## Conservative ColorMix algorithm

1. Keep the **original 16-color PAL0 exactly unchanged** for all 14 PLAYPAL subpalettes.
2. Offline, select 15 extra Doom source colors based on quantization residual error; load them into PAL1 indices 1..15. PAL1 index0 remains transparent.
3. For each PAL0 base index (0..15), choose two PAL1 indices whose displayed spatial average (2:2, 3:1, or 1:3) best approximates the residual color clusters, with penalty on high-contrast 2px/1px stripes.
4. For each of the 14 PLAYPAL variants and 256 original DOOM color indices, enable mixing **only when its predicted squared RGB distance is at least 8% below the original solid**, with an extra absolute margin.
5. For Pair-V, the upper and lower 4px samples are independently gated. Only when **both** sample flags are enabled is the PAL1 patterned tile bank chosen. Any failure causes a direct fallback to the exact original PAL0 solid pattern **for both**.
6. Store the two eligibility flags in the already-existing high byte of each tilemap word, not in extra WRAM. This yields four 256-tile pattern banks:
   - Bank 0 (base 256): no eligible sample → PAL0, exact solid;
   - Bank 1 (base 512): only upper eligible → PAL0, exact solid;
   - Bank 2 (base 768): only lower eligible → PAL0, exact solid;
   - Bank 3 (base 1024): both eligible → PAL1, mixture.
7. All 1024 tiles occupy indices 256..1279, below the SGDK font at index 1440.

The gate is a conservative **RGB-space model**, not a guarantee of perceptually invisible dithering. Alternate PAL1 colors must be judged on CRT / HDMI output, with temporal and spatial aliasing taken into account.

## LUT experiment

`DOOM_R49_COMPLUT` generates a ROM-only LUT to collapse `r22_color[COLORMAP[level][source]]` into one lookup. A fallback is used for unexpected colormap pointers. The ColorMix+LUT experiment also uses a separate eligibility LUT per PLAYPAL subpalette. Measure real FPS — extra ROM loads or less favorable cache locality can negate gains.

## Fixes and validation

- `src/r35_native4.inc`: clear both background planes when leaving native pictures, wait for DMA, restore palette/tiles and framebuffer.
- `src/r22_video.inc`: clear Plane B alongside A when presenting timedemo results.
- `scripts/lab/test_r48_pair_v.py`: Pair-V geometric oracle.
- `scripts/lab/test_r49_colormix.py`: verify palette gates and legal VDP tile attributes for all 14 subpalettes.
- CI: 15 ROM builds, strict BSS ≤ 57920 B, BlastEm fast completion smoke on all PERF variants, SHA256 manifest.
- Manual: full DEMO3 timedemo at BlastEm divisor 7, PLAY E1M1 transitions, menus/HUD/health/ammo, visual inspection, real Mega Drive/EverDrive.

**No measured ColorMix performance or perceptual superiority is claimed by this document.**
