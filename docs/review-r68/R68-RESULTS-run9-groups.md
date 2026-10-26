# R68 run 9: SPLIT + phases + function groups (run 40345181424, head ca3a9d0)

Maintainer-authorized 18000-frame capture. 912 game frames, tics 0..912 (about 43% of DEMO3), mean 9.79 vb/frame
under profiling overhead (not a benchmark). Phases: logic 11.1%, setup 2.1%, BSP+walls+planes 77.1%, masked+sprites 9.0%,
HUD 0.1%, flip+video 0.6%.

PC samples by group (all frames / third 1 / third 2 / third 3):
| group | all | t1 | t2 | t3 |
|---|---:|---:|---:|---:|
| wall column C glue | 30.5 | 37.0 | 24.1 | 25.6 |
| segment setup + geometry | 15.0 | 15.0 | 10.1 | 18.2 |
| flat span/column | 10.2 | 12.7 | 2.4 | 11.8 |
| wall kernel (ASM) | 9.3 | 5.5 | 18.9 | 8.3 |
| sprite/masked draw | 7.9 | 7.3 | 11.9 | 6.0 |
| BSP traversal | 7.6 | 7.4 | 4.4 | 10.0 |
| game logic | 6.9 | 4.6 | 12.9 | 6.4 |
| other | 6.8 | 5.4 | 9.7 | 6.9 |
| map streaming | 3.5 | 3.0 | 3.0 | 4.5 |
| sprite project/sort | 2.3 | 2.1 | 2.5 | 2.4 |

Third 1 (tics 0..304) averages 13.5 vb/frame, third 2 only 6.2 vb/frame. Mean FPS is dominated by the wall-C-glue heavy sections.
