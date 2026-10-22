# R52 Pair-V AB ColorMix — build and visual QA

## Provenance / isolation
- Branch: `r52-ab-colormix-matrix` from R51 V2 commit `292a6a69e19daf26c797ac119b90e3bfadc7d906`.
- Experimental only. Do not merge into `r50-native-menu-mask-fix` or the default branch until PLAY and hardware tests pass.
- R51 hardware gun is deliberately OFF in the entire R52 color matrix: the visual artifact and FPS signals must come from the palette strategy, not HUD clipping or sprite masking.
- External source: R52 external audit4 `AB_near25` and `AB_luma32` (P0/P1 source representatives plus 256-entry parity maps).
- R52 **repairs index 0**, because color index 0 on a VDP tile is transparent. The generator replaces one least-used opaque palette slot in each plane with an opaque black and remaps both index-0 pixels and the displaced color. **The external simulation's ΔE values are therefore not valid measurements of the built R52 ROMs.** Reevaluate captured images.

## Implementation
- Plane A / even 4-pixel columns = 16-entry CRAM PAL0.
- Plane B / odd 4-pixel columns = 16-entry CRAM PAL1.
- Pair-V 3,344-byte framebuffer unchanged; per-tile palette bits are initialized in `R47_ClearPairBuffer` and survive VBlank DMA.
- Wall, sprite/fuzz and flat kernels select ROM maps by screen-x parity; AB builds do not invoke R49 per-sample gate or rewrite `dst[-1]`.
- Native full-screen art preserves its own palette; gameplay palette is restored on exit to E1M1.
- All 14 Doom subpalettes are materialized via PLAYPAL. Their perceptual equivalence **has not been validated**.
- The previous R49 scheme remains a separate A/B control, not incorporated into the AB variants.

## Eight ROMs

| ROM suffix | Mode | Strategy |
|---|---|---|
| `c0-vf-perf` / `c0-vf-play` | PERF / PLAY | Original Pair-V Fast control |
| `c1-cm50-perf` / `c1-cm50-play` | PERF / PLAY | R49 ColorMix 2:2 plus composed LUT |
| `ab-n25-perf` / `ab-n25-play` | PERF / PLAY | Dual palette, near25 frozen seeds + opacity repair |
| `ab-l32-perf` / `ab-l32-play` | PERF / PLAY | Dual palette, luma32 frozen seeds + opacity repair |

ROM prefix: `doom-md-r52-`. No ROM is certified until GitHub Actions succeeds.

## CI gate
1. Verify fish toolchain, WAD SHA256, audio and Pair-V oracles.
2. Recompute R49 baseline and independently materialize both AB profiles.
3. Reject AB LUT indices outside 1..15 (avoid unwanted VDP transparency).
4. Build 8 ROMs, verify BSS <= 57,920 bytes, check filename/header identity.
5. Execute BlastEm 800-frame boot smoke on every ROM.
6. Upload binaries, palette reports, preflight tables, SHA256 manifest and build-flag records.

**Smoke testing does not prove visual output, a successful DEMO3 result or safe operation on Mega Drive hardware.** No compilation was executed in this conversation; workflow is queued for self-hosted runner.

## Manual tests (same tic and machine settings)
- Capture same E1M1 / DEMO3 frame on C0, C1, N25 and L32.
- Compare native-pixel 320x224 (RGB/HDMI/no blending) first, then CRT/NTSC composite filtering; watch 4px vertical bars.
- Test walls with subtle textures, floor/ceiling, dark areas, green lights, red/brown enemies and muzzle flash.
- Confirm HUD text brightness/contrast, title and menu art, restart, New Game, health, ammo, benchmark return and palette tint transitions.
- Compare benchmark seconds/FPS on all four PERF ROMs at identical BlastEm divisor 7, ideally two runs each.
- Baselines from prior user runs (not new R52 measurements): VF 5.31 FPS; CM50L approximately 5.03 FPS; no gun 5.52 FPS (different ablation, NOT equivalent to the R52 color variants).
- Select final strategy by visual quality **without filters**, perceived shade diversity, fewer stripe artifacts and FPS. Do not claim 32 simultaneously distinct flat colors per pixel or VDP alpha blending.

## Rollback and further work
- If all AB ROMs have visual regression, keep `c0-vf` and original R50.
- If index0 repair degrades dark gradients, rerun offline optimization with mandatory 1..15 opaque indices and rebenchmark, rather than declaring the originally simulated ΔE values valid.
- If the status-bar text loses brightness due to PAL0 reassignment, isolate its font palette without disturbing native-art palette use.
- Do not combine this experiment with R51 HUD sprite fixes in the first run.
