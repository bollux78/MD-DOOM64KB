# R50 feedback and next ColorMix evolution (R51 planning)

## Verified by manual PLAY/BlastEm tests

- `vf-bf-play` and `vf-ctrl-perf`: respectively ~5.30 and 5.31 FPS, 2,134 DEMO3 frames.
- `cm50l-bench-play` and `cm50l-ctrl-perf`: respectively ~5.02 and 5.03 FPS, 2,134 frames.
- Freeze-3D-on-menu improves controller responsiveness substantially during live gameplay.
- Benchmark entered from E1M1 now reaches results, returns to main menu, and permits New Game after return (R50 return-fix manual confirmation).
- Title native art is obscured by full-screen WINDOW during menu (menu visible over black with a strip of title only at bottom).
- Soft reset during an active benchmark has produced black screen; root cause not proven. Test cart SRAM overlay and VDP re-enable independently.
- ColorMix sometimes reveals spatial details otherwise crushed together, but user does **not** yet perceive a genuine increase in visible color range. Visual quality needs revision.

## R50 isolated corrections

Branch `r50-static-menu-reset-fix` retains Pair-V Fast, ColorMix, on-demand timedemo and no-3D menu.

- Static art fix: avoid putting full-screen WINDOW over native title. Write high-priority menu glyphs directly on BG_A over mirrored native art in BG_B, with byte-mask tracking of glyph cells and exact ROM tilemap restoration for stale glyph positions. Keep 320x224 native palette/picture and avoid new WRAM framebuffer.
- **Reset hypotheses not yet discriminated:** (a) a soft reset during mapmem may leave SRAM register A130F1 enabled, masking ROM at 0x200000; the current experiment disables it at entry to main and re-enables VDP after video init. (b) Sega's official Genesis Software Manual describes soft reset during VDP DMA leaving DMA active, because the VDP is not reset; subsequent VDP initialization accesses can be ineffective. This second failure could happen *before* main, in SGDK startup. The current C-entry guard does not yet address it. Validate art-only/reset-only/combined A/B and do not claim a full warm-reset fix without empirical testing. See https://segaretro.org/images/9/95/GenesisSoftwareManual.pdf ("Repeated Resets").
- Six A/B builds separate both fixes: control, art-only, reset-only, combined, ColorMix combined and VF PERF.

## R51 ColorMix research questions

1. **Why PAL1 colors do not appear genuinely new:** the R49 generator chooses 15 additional hardware palette colors from the original PLAYPAL, but selects a single pair of PAL1 indices **per one of just 16 quantized PAL0 classes**, not per original Doom source index; many selections may be identical or near-identical. Its gate additionally rejects pairs unless predicted averaged squared-RGB error improves by at least 8% and 64 absolute units, with stripe contrast penalized. When only one vertical 4px half is eligible, both samples fall back to PAL0.
2. **Quantify rather than infer:** report how many of the 16 classes have distinct A!=B partners at each ratio, gate coverage for each of 14 subpalettes, palette-index occupancy in timedemo, visible-pattern distribution, and exactly how often fallback happens because only one sample is eligible.
3. **Optimize on rendered scene statistics:** weight candidate palette and pair selection by frequency in E1M1 (plus a holdout from other E1Ms), not uniformly across 256 PLAYPAL entries. Preserve uncommon colors when they convey gameplay-relevant features.
4. **Test *within-4×4* spatial dithering**, including a Bayer 2D allocation rather than contiguous 2+2 vertical stripes, to avoid directional artifacts and potentially create visible intermediate tones using PAL0 alone. Because VDP pixels are opaque, this is spatial dithering, not hardware alpha blending.
5. **Check tilebank limits:** Pair-V uses 256 base patterns and R49 uses 3 more 256-pattern banks. One cannot freely choose independent palettes for top and bottom 4px fragments because a VDP tile has one palette selection. Existing banks 1/2 are redundant PAL0 repeats and may be repurposed only after auditing color/palette constraints and preserving tile-index bounds (< SGDK font tile 1440).
6. **Separate geometry detail from color fidelity:** side-by-side captured frames aligned to identical DEMO3 tic; inspect reconstructed 4×4 scene versus original source palettes at native display size. Use objective MSE/CIEDE2000 and user review without claiming metrics prove perceptual preference.
7. **Performance target:** retain VF ALL (~5.31 FPS) as the primary baseline; ColorMix quality variants should be accepted for genuine visible improvement, with overhead explicitly measured against 5.30 PLAY / 5.31 PERF.
8. Pair-H remains a **single historical control**, not a regular test family.

### Acceptance

Do not declare ColorMix richer because the palette table has 15 more physical entries. It must create additional **distinct, useful visible shades** in actual gameplay compared with the VF control and preserve map clarity, shading gradients, sprites and HUD. Keep visual fidelity and FPS as separate metrics.
