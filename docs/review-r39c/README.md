# R39c — SRAM optimization A/B, derived from R38
Base: `r38-time-profile`, clean DEMO3 = 2,134 frames, 191.20 s / 11.16 FPS on BlastEm divider 7.

## One change at a time
- `control-cell-perf`: R38 unchanged.
- `mcache-cell-perf`: P1 MOVEP.L cache transfers only (`DOOM_R39C_MOVEP_CACHE`).
- `mmap-cell-perf`: P1 MOVEP SRAM map primitives, blocklinks and R27 grouped reads (`DOOM_R39C_MOVEP_MAP`).
- `mall-cell-perf`: combination of those two P1 subsystems (only if each is stable).
- `reuse-cell-perf`: P2 remember current multipatch column already in tmpCache; skip redundant SRAM reload (`DOOM_R39C_REUSE_CACHE`).
- `mall-cell-play`: gameplay validation of experimental MOVEP code, especially SRAM mapper/EverDrive.

These are hypotheses, not yet speedups. No R39a clip scanner or R39b TEX4 stretched textures are included.
Header generation knows `r39c` ROMs map 4MiB before trimming. Names are max 30 chars.
There is an SRAM byte-order startup probe for map MOVEP variants; it restores previous bytes.

## Safety
- MOVEP uses spaced byte addresses 0x200001,0x200003,..., never contiguous RAM.
- P1 cache aligns `tmpCache` to at least two bytes for 68000 long reads.
- `R25_SRAM_BEGIN/END` are unchanged and guard all mapper access.
- On real hardware an SRAM failure could affect game/save state; validate in emulator first and back up saves before hardware test.
- A compile, hash or 300-frame smoke test does not prove 2,134-frame DEMO3 correctness; run to completion.

## Further independent experiments
1. P4 R38 sampling fix: multipatch texture draw measured as W, not C; compare detailed stage shares with corrected instrumentation, **never** use instrumented FPS as control.
2. P3 precomposed multipatch columns in ROM (check true serialized size and SRAM ROM window; no SRAM/ROM simultaneous access).
3. P5 validcount bitset in WRAM (track all ++ sites, callers and save/automap semantics).
4. P6 conservative cross-product culling and R_AddLine vertex reuse, one change per variant.
5. P7 special-case integer wall heights and rowoffset modulation, separate each.
6. P8 assembly pixel unroll x4, audited with a pixel-output hash and boot/level checks.
7. Original handoff: flat/ceiling run fast path, wall-column buffer/lookup hoisting and per-frame cache reuse; verify earlier R20/R21 results before revisiting.

## Benchmark gates
- Baseline 11.16 FPS, 191.20s, 2,134 frames; no instrumentation or overclock.
- Each candidate records FPS, min/max, DEMO time, checksum/error and scene appearance.
- Repeat winners three times and compare A/B on real Mega Drive clock.
- Only combine independently positive candidates after separate comparisons.
