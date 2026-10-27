# R73 — R53-N25F-M25 on R71A12MUL-HUD (experimental)

## Scope

Baseline: `exp-chatgpt-r71a12mul-hud-20261026` via R72 experimental branch.
Mandatory: original Doom HUD-WAD, R71 MUL ASM, R64A, H40 stone margins.
Do not merge until real-hardware visual and PERF review.

This experiment **does not use CM6 as active palette**. It generates the original R52
`near25` / zero-forbid CRAM words and both parity LUTs, then adds R53's
25% partner microdither. R59's table/VDP infrastructure remains linked, but
mode zero is replaced with the R53 derived profile; options palette selector
is compiled out only for this branch's test ROMs. Original R59 modes remain
in ROM as inactive data (space cost not yet optimized).

## ROMs

| name suffix | codebook | flat parity | type |
|--|--|--|--|
| r73-r53-solid-perf / play | exact R52 palette, solid 4-pixel row | unchanged | PERF / PLAY |
| r73-r53-m25-perf / play | R53 rotating 25% microdither on tile pixels | unchanged | PERF / PLAY |
| r73-r53-m25-flat2d-perf / play | same M25 tile patterns | alternate even/odd each y | PERF / PLAY |

All six retain HUD. If a ROM shows unchanged CM6 visuals, reject it.
Compare PLAY screenshots from a fixed position to the approved R53
`r53-n25f-m25` example. Compare PERF with R71-HUD reference 7.32 FPS
on DEMO3, NTSC 60Hz, original Mega Drive clock.

## Build

Workflow: `.github/workflows/r73-r53-tests.yml`.
Runner: self-hosted Linux x64 with MarsDev, fish and source WAD at pinned
path. Workflow generates graphics, applies two disposable source patches,
isolates each build tree, then publishes `dist/hud` with six BINs, ELFs,
headers, checksums and manifest.

The R52 LUTs are byte-for-byte sourced from `gen_r52_claudio.py --mode near25
--zero-policy forbid`; the original R53 partner generator uses the corresponding
R52 report. An additional independent visual equivalence test to a historic
R53 ROM is not implemented; only runtime screenshots can establish fidelity.

If compilation fails, inspect the run logs and report exact failed step before
editing the stable branch. The experimental branch carries the inherited
`build_silent.fish` fish-quoting repair from R72, applied only to the isolated
checkout; no changes to baseline R71.

## Caveats

The R53 palette and tile microdither are carried into the optimized
R56/R59 Pair-V renderer; the result may differ from R53 because R71
has changed clipping, viewport, HUD and wall arithmetic. The M25-flat2d
variant additionally samples the other parity's flat map by logical y;
its colors may become patchier, and is intentionally a separate test.
No measured ROM FPS or verified hardware image is claimed here.
