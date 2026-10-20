# R46 M2C/P2A — native spans and BSP solid-column scratch

Base: approved M2C/P1, 11.80 FPS / 180.82 s / 2134 DEMO3 frames, three ROMs accepted.

This is the first slice of P2, **not yet a complete 4x4 renderer**.
- `r46_pixel4_spans.c/.h` introduce callback-driven row-span transitions in 76x44, backed by caller-provided 44-byte row starts.
- Solid columns use a caller-provided 76-byte array; no persistent duplicate scratch memory.
- The active R39f 8x8 path is not modified.
- No sky/weapon/VDP allocation or game resolution switch is attempted.
- Later P2 pieces still need full BSP angular traversal, visplane allocation/ownership, camera-space sprite transforms and integration into the native draw pipeline.

Acceptance: independently compile and run host tests; verify no duplicate .bss and no 8x8 performance regression after CI integration. Do not conflate P2A helper availability with runtime 4x4.
