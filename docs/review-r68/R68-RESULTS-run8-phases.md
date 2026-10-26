# R68 run 8: phase timing (run 40335885835, head db717d4, no SPLIT)

444 frames (first ~450 demo tics), mean 10.95 vb/frame under profiling overhead (not a benchmark).

| phase | mean cycles | share |
|---|---:|---:|
| logic (TryRunTics) | 151362 | 10.8% |
| setup (R_SetupFrame..clip init) | 24260 | 1.7% |
| BSP + walls + planes | 1079998 | 77.1% |
| masked + sprites | 136355 | 9.7% |
| HUD/menu | 881 | 0.1% |
| page flip / video | 7946 | 0.6% |

Conclusion: the "fixed per-frame cost" from the regression intercept is NOT setup, HUD or flip (about 2.4% together).
It sits inside BSP+walls+planes (work not explained by the counters) and in logic (10.8%).
Resolution: one V-counter line (~487 cycles); stamps in vblank lines 229-240 are ambiguous (decoded as the first pass).
