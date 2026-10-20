# R46 M2C/P2G — two independent native sprite primitives

User-approved P2F baseline: 11.80 FPS / 180.82s control; 11.78 FPS / 181.12s M2C; 2134 frames each; all three ROMs functional.

This batch introduces two independently host-tested primitives:
1. Stable far-to-near order of up to 128 sprites, using caller-provided
   depth and index arrays; no heap, preserves order among equal depths.
2. Multiple visible segments within one native 76x44 projected sprite
   column using caller-provided 44-bit occlusion mask.

Both remain isolated from the active R39f 8x8 pipeline. No ownership of
actual drawseg windows, depth masks, masked textures or hardware sprite
resources is asserted. It does not activate the 4x4 renderer or alter sky/
HUD/weapon architecture. 64-bit mask operations need 68k performance
evaluation before live wiring.

CI generates control, experimental PERF and PLAY ROMs with host tests,
linked-symbol and RAM audit, ROM integrity checks and BlastEm smoke.
