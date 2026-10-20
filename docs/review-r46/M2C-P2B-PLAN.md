# R46 M2C/P2B — guarded native visplanes + BSP open runs

Base: user-approved R46 M2C/P2A (primary and M2C both 11.80 FPS / 180.82 s / 2134 frames).

Added:
- Native visplane window with 76 drawable columns and two sentinels for `x-1` and closing `stop=76`.
- Plane range joining, overlapping-column detection, top/bottom assignment.
- Contiguous maximal BSP visible-run iterator from caller-owned `solid[76]`.
- Host C oracle: 10,000 BSP masks and guarded plane edge cases.
- Zero persistent duplicated scratch/framebuffer. Standalone metadata boot check; 8x8 is still sole rendering path.

Not yet done: Doom visplane allocations/ownership within the renderer, full angular BSP traversal, world-space sprite transformation, and complete native draw pipeline. M3 VDP/VRAM handoff and M4 live toggle remain separate gated work. Never present P2B as playable 4x4.
