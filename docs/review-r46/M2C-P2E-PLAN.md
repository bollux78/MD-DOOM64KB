# R46 M2C/P2E — native sprite wall/depth + vertical clipping

Baseline: P2D three ROMs approved. DEMO3 control 11.80 FPS / 180.82 s / 2134 frames; P2D experiment 11.78 FPS / 181.12 s / 2134 frames.

This phase adds R46_P4_SpriteVisiblePost(), a pure scalar test of a
76-column projected sprite post against optional solid wall depth and
caller-owned ceiling/floor clip arrays. 30,000 randomized oracle cases.
The function does not modify active R39f buffers. Metadata-only startup
validation retains symbols in the optimized ELF. No permanent BSS arrays.

**Scope limitation:** This is a visibility primitive, not a complete Doom
drawseg portal/masked clipping implementation; no perspective-correct sprite
texture columns, patch selection, depth-sorted sprite queue, BSP traversal,
native plane renderer, VDP handoff or runtime toggle are introduced.

Gate: build three ROMs and pass native host oracle, .bss and ROM integrity,
BlastEm smoke; then compare complete DEMO3 and test PLAY. Track 0.30 s P2D
difference, do not claim performance improvement without measured evidence.
