# DOOM MD — R29 / XGM2 experimental builds
This experiment is isolated from r28-sram. Assets and game renderer stay unchanged.
- group-perf: R28 XGM classic, complete music, baseline.
- xgm2-low-fixed / xgm2-low-group: E1M1 reuse, XGM2, SRAM fixed.
- xgm2-multi: complete soundtrack compiled in a shared XGM2 multitrack resource.
- xgm2-multi-play: playable version of multitrack.
- xgm2-single: complete soundtrack as separate XGM2 resources.
XGM2 uses three PCM channels. We reserve channel 1 for music and channels 2/3 for SFX.
SFX input PCM is sampled as for classic XGM; the slightly different DAC sampling rates
may affect pitch and must be tested. Do not claim correct audio or FPS from compilation.
The R28 heap diagnostic failure 9 with fixed SRAM is not fixed by this audio experiment.
Pass criterion for SRAM fixed: ROM size <= 2097152 B AND zero heap diagnostic errors
AND verified behavior on BlastEm and original hardware. Fullscreen art/compression
not changed in this first R29 branch.
