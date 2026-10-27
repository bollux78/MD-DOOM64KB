# R74 implementation and validation — 2026-10-27

This experimental branch integrates the two collaborator proposals. Status: **source + workflow prepared; hardware and runner-build success must be verified**. Stable R71A12MUL-HUD is untouched.

## Input references

- User visual preferences: R53-N25A-M50 and R53-L32F-M50; R73-F coarse logical-grid dithering rejected.
- Werk: M50 already uses physical 1x1 checker, not logical line-flipping. Near25/allow vs luma32/forbid. Compare actual effective M50 colors.
- Claudio: flat-specific even/odd mapping; compute contrast *after* same-palette companion mix; penalize column discontinuity and preserve hue.
- Embedded scripts regenerate profiles from the same source WAD and quantized CRAM. No claim of byte-for-byte equality to historical ROMs until historical header hashes are compared.

## Sixteen ROMs in the first R74 batch

| Profile | Control PERF/PLAY | F1 PERF/PLAY | F2 PERF/PLAY | F3 PERF/PLAY |
| --- | --- | --- | --- | --- |
| N25A / near25 / zero allow | r74-ac-pf/pl | r74-a1-pf/pl | r74-a2-pf/pl | r74-a3-pf/pl |
| L32F / luma32 / zero forbid | r74-lc-pf/pl | r74-l1-pf/pl | r74-l2-pf/pl | r74-l3-pf/pl |

- Controls retain the original R52 flat mappings, including any allowed zero.
- F1 = nearer effective PAL0/PAL1 colors.
- F2 = balanced proximity/fidelity, with target-error gating.
- F3 = strict deltaE/luma gating with explicit fallback where physically unavailable.
- F variants choose only opaque flat indices 1..15. This is especially useful for N25A where transparent zero can create visual holes.
- All variants use **the same M50 partner-generation ratio, physical 1x1 checker**, HUD-WAD, H40 stone margins, R64A, R71 MUL ASM.
- **No** R72_FLAT_2D/R73-F coarse checker. **No** HUD-less diagnostic ROM. **No** sky changes in this first batch.

## Implementation

- `scripts/lab/apply_r74.py`: applies previous R73 build isolation and changes its historical 25% density to 50%; selects 16 variants and explicit per-profile zero policy.
- `scripts/lab/gen_r74_flats.py`: enumerates 225 opaque pairs per each of 256 colors, calculates effective M50 CRAM slot colors and emits two ROM LUTs.
- `scripts/lab/inject_r74_flats.py`: switches only the R59 mode-zero flat-even/odd aliases; wall, composed-colormap, palette and tile-companion lookup maps remain unchanged per control.
- `.github/workflows/r74-m50-flats.yml`: self-hosted builds, Python preflight, sizes/BSS, manifest, hashes and artifacts. Generates reports per ROM.
- `DOOM_HUD_WAD` is mandatory.

## Testing gates

1. Confirm all sixteen `.bin` + `.elf` and `*-flat-report.json` files appear, plus flags and SHA-256 manifest. Check BSS <= 57920, ROM <= 4 MiB.
2. Compare each flat-optimized PLAY ROM with its **same-profile control**, not with the other profile. Walls and sprites must not regress.
3. Prefer homogeneous blue/green/gray flat regions with no washed-out hue, black holes or R73-F coarse mosaics.
4. PERF benchmark: 60 Hz NTSC, DEMO3, original clock. R71-HUD historic 7.32 FPS is context; the relevant delta is vs integrated control.
5. Never infer FPS performance from an instantaneous screenshot. Capture DEMO3 frames and elapsed time.
6. Historical N25A/L32F palette identity needs source/header hash verification. Reconstruction from the original generators is described as such.
7. Sky tile scrolling is a separate future ROM, not included here.

**Caveat:** optimization uses PLAYPAL bank0 as target but CRAM M50 entries are banked for 14 PLAYPAL effects. The selected indices are stable across banks; visual impact of flashes must be verified.
