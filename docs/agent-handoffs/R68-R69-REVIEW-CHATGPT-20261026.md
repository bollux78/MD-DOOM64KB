# ChatGPT independent R68/R69 review — 2026-10-26

Read-only review of Claudio's R68/R69 reports and source; no builds, merges, or workflow dispatches.

## Verdict
**Proceed with an isolated, source-level optimization experiment with pixel equivalence tests first.** This is not approval to promote a baseline or claim FPS. R66 f5a9daa remains immutable.

## Important findings
1. **HInt sampling bias and grouping** — `scripts/lab/r68_capture.py:28-45,128-130`. The measured 30.5% "wall column C glue" is a *group* comprising R_RenderSegLoop, R42_DrawPackedWall, R_DrawSegTextureColumn and R_GetColumn; it is not 30.5% solely R_RenderSegLoop. The 15% "segment setup + geometry" includes generic multiplication/division routines, so avoid claiming the entire share belongs to R_StoreWallRange. Sampling excludes VBlank, so the denominator is active-line PC samples, not whole-frame CPU usage. Instrumentation and noinline may alter the code path.
2. **Phase marking quantization** — `scripts/lab/r68_capture.py:62-79`: 0xE5..0xEA ambiguity (6 lines) at the V-counter wrap can perturb short phases; report shares as estimates and quantify sensitivity/error bars for the short setup/video phases.
3. **Sampling bucket precision** — `scripts/lab/r68_capture.py:128-130,272-304`: stored PC>>3 is quantized to 8-byte buckets and symbols resolved by nearest lower start; avoid overconfident source-line attributions, particularly at function boundaries or for inlined code. Review compiler .elf and `hot.md` hotspots.
4. **Observation window** — `docs/review-r68/R68-RESULTS-run9-groups.md:1-19`: 912 tics (~43% DEMO3); 13.5 / 6.2 / 9.7 vblanks/frame in thirds, so the workload is strongly scene-dependent. Avoid generalizing to the full game.
5. **R69 crops** — `docs/review-r69/R69-RESULTS.md:1-18`: variants are instrumented and compared on matching 342 tics. Crop-versus-area is sublinear; estimated stock-clock FPS extrapolations are projections, not measured FPS or approved visual tradeoffs. Table lists six distinct entries although the text/workflow says seven ROMs: confirm which seventh file is a control.
6. **Inertness proof scope** — `scripts/lab/check_r68_inert.py:6-64`: comparison is normalized **source** across seven files, not a general binary-equivalence proof; R66 `cmp` in CI is the actual byte-level safeguard. Keep both.
7. **Workflow explicit controls** — `.github/workflows/r68-prof-build.yml:1-18,80-103,164-203`: branch/path-restricted push; pinned local WAD; 18,000 emulated frames documented as maintainer-authorized. Keep workflow execution separately authorized for any new branch/experiment, with separate artifact and no unreviewed runner execution.
8. **Coverage discrepancy** — R68 reports explicitly leave unexplained how BlastEm -b counts relate to recorded vblanks. Investigate before using the run duration as a coverage claim beyond game tics.

## Main hypothesis
I agree **directionally** that C work associated with wall columns and per-segment geometry is a better first optimization target than the wall ASM kernel, based on run6 and run9 group sample shares. This is an optimization priority, not proof of marginal cycle savings. First inspect disassembly at the PC hot buckets and partition wall C functions and generic math functions separately.

## Proposed R70 experiment protocol
- New branch based on the R66/R68 feature ancestry, **leave R66 baseline and R68/R69 instrumentation unchanged**.
- First create host tests for pixel/output equivalence on representative scenes, clipping, horizon, textured/untextured, odd/even R66 paired columns, flats and masked sprites. Add ASAN/UBSAN host tests where practical.
- Change one concept at a time: (A) remove redundant global loads/stores and per-column invariant recomputation from `R_RenderSegLoop`; (B) reduce redundant per-column glue in `R42_DrawPackedWall` / `R_DrawSegTextureColumn`; (C) hoist segment invariants and avoid repeated costly math in `R_StoreWallRange`. Preserve fixed-point rounding, overflow behavior, colpair reuse, clipping and sample order. Avoid algorithm changes and quality reductions.
- For each candidate, compare unmodified and optimized builds at the *same* crop H40 16/16 with official stock-clock measurement, same DEMO3 segment and R66-identical visual output; report ROM bytes, BSS (R66 57,900 B; budget <=57,920 where applicable), per-scene frame times and representative frame hashes/pixel differences. Diagnostics with SPLIT/instrumentation do not establish FPS gains.
- Stop/revert if any pixel mismatch or negligible gains; promote only after user hardware validation.

## Requested additional evidence
- `dist/r68/capture/hot.md` and exact per-function PC counts for `R_RenderSegLoop`, `R42_DrawPackedWall`, `R_DrawSegTextureColumn`, `R_StoreWallRange`, `FixedMul`, `__mulsi3` and `R60_WallColumn`.
- Uninstrumented A/B ROM pair and host frame output hashes; matching scene conditions and BlastEm configuration.
- Explicit breakdown of 18,000 emulated BlastEm frames vs 912 game frames/vblank stamps, dropped samples/bad frames, and the seventh R69 build target.

No code changes or workflow executions made by ChatGPT during this review.
