Tue Nov  3 01:28:20 UTC 2026

Run requested for R116 demotest from branch head f302d7973d30; retain ROMs and demos private.

R116 probe fix experiment: configure selected demo before G_DoPlayDemo and reject any FAIL (CI gate).

R116 test gate v2: stable G_Ticker breakpoint + explicit r116_active verification; no missing optimized symbol.

R116 safety pass: allow gameplay deviations; check live ticker progress, zone, I_Error, return code and bounded completion.

R116 direct Benchmark Run All sequence, 10 demos, unchanged H32/H40 crop Shadow palette and AI Options; aggregate FPS.

R116 Run All hardening: common safe PERF+PLAY handoff, repeated-demo-end guard, noipa symbol for RSP smoke.

R116 benchmark accuracy v2: 64-bit consistent FPS/time, runtime invariant, exclude map transitions from 1-second min/max.
