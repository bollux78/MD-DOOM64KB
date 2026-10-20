# R40c M0 — Resultados manuais DEMO3 confirmados (20/10/2026)

Testes realizados no BlastEm, NTSC 60Hz, DEMO3 **2134 quadros** em todas as ROMs; usuário confirmou que as ROMs jogáveis funcionam.

| ROM | FPS médio | Tempo DEMO3 | Mín 1s | Máx 1s | SGDK free / max block |
|---|---:|---:|---:|---:|---:|
| `doom-md-r40c-cell-perf` | **11.80** | **180.82 s** | 4.3 | 22.0 | 1386 / 1386 |
| `doom-md-r40c-pixel4-perf` | **3.01** | **709.67 s** | 1.8 | 3.9 | 862 / 862 |
| `doom-md-r40-cell-perf` (older reference) | 11.80 | 180.82 s | 4.4 | 22.0 | 1386 / 1386 |
| `doom-md-r40-fast-pixel4-perf` (older) | 3.01 | 708.37 s | 1.8 | 4.0 | 864 / 864 |
| `doom-md-r40-base-pixel4-perf` (older) | 2.87 | 744.85 s | 1.6 | 3.6 | 862 / 862 |

**Assessment:** integration M0 is performance-neutral at displayed FPS precision (8x8 11.80 and pixel4 3.01). The +1.30 s (~0.18%) in the 4x4 case must not be proclaimed a significant regression without repetitions. These are independent compile-time backends, NOT a runtime 8x8/4x4 toggle.

**Menu screenshot caveat:** user showed ghosting in **`doom-md-r40-fast-pixel4-play`**, the pre-R40b ROM, not the newly built `doom-md-r40c-pixel4-play`. Git blob IDs for `src/r22_video.inc` and `src/r35_native4.inc` are identical in R40b and R40c. Do not automatically ascribe this ghosting to R40c; verify the R40c play level-selection menu before changing overlay code.

**M0 CI:** [run 39348218663](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39348218663) ([artifact 12232356511](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39348218663/artifacts/12232356511)); ROM headers/size/flags, LUT regression, 300-frame smoke passed.

**Next product milestone:** M1 dual coexistence in one linked ROM, M2 geometry separation, M3 synchronized VDP/CRAM reconfiguration, M4 Options selection without resetting current map/player. No dual executable exists yet.
