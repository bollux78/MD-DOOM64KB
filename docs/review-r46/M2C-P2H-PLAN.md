# R46 M2C/P2H — integrated geometry pipeline (two changes in one build)

User-approved baseline P2G: control 11.80 FPS / 180.82 s; M2C 11.78 FPS / 181.12 s, 2134 frames each.

Changes bundled in three-ROM integration build:
1. Guarded native 76x44 visplane owner -> 44-row span transition sweep,
   emitting spans through a caller callback. No VDP coupling.
2. Stable sprite depth sort -> 44-bit occlusion mask -> per-column
   multi-post callback, passing sprite identity and visible pixel rows.

Both paths use existing M2C/P2A–P2G modules and **caller-provided scratch**.
The 8x8 R39f renderer is the sole gameplay path. This tests actual
module composition, not just separate helpers, without adding duplicate BSS.

Still not implemented: full Doom BSP traversal or drawseg-to-row occlusion
mask generation, complete native sprite patches and texture columns, sky
plane-B or hardware-weapon sprites, VDP ownership, resolution toggle or
playable 4x4 renderer. These remain gated by native frame integration.

Pass criteria: host integration oracle (plane sweeps, ordering and row
occlusion), three ROM builds, ELF retained symbols and BSS audit,
ROM integrity, BlastEm smoke, then full DEMO3 + manual PLAY comparison.
