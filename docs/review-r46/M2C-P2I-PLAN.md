# R46 M2C/P2I — packed 4bpp CPU preview composition (two modules)

Baseline approved by user: P2H three ROMs, no functional problems, DEMO3
control 11.80 FPS / 180.82 s, experimental 11.78 FPS / 181.12 s,
2134 frames, no errors. Keep primary R39f 8x8 playable and unaffected.

## Included together

1. **Native pixel target**: caller-owned 1672-byte buffer, packed
   high-nibble-even / low-nibble-odd 76×44 pixels, guarded row and
   column stores. Optional first 2 sample rows reserved for topbar.
   No added global framebuffer or VDP/CRAM/interrupt writes.
2. **Offline composition**: actual P2H guarded plane span sweep and
   depth-sorted/masked sprite post callbacks now write to the packed
   pixel target in flat palette-index colors. Sprite order and row masks
   are caller provided, and validated before buffer mutation.

This introduces a **CPU-side, fully testable composition path for synthetic
geometry**, not a fully wired Doom renderer. Colors are flat test indices;
there is no real wall/flat texture lookup, perspective texture sampling,
sector lighting or WAD patch/rotation selection in this compositor.

No runtime call to compose against `_s_screen` is enabled while R39f
owns the shared tile-word framebuffer. No DMA, VRAM bank switching,
hardware sprites, Plane B sky, dual-mode dispatcher, 4×4 gameplay or
FPS speedup is claimed. CPU cost must be measured before enabling it.

## Acceptance gates

- Host C oracle: nibble parity, 1672-byte bounds, preserved first two
  sample rows, scene composition, far-to-near sprites, partially occluded
  near sprite, invalid-input nonmutation.
- Three ROMs: primary PERF; M2C PERF; M2C PLAY.
- Link retained functions, no extra .bss vs primary, 4 MiB linear ROM
  maximum, header/flags, 300-frame BlastEm smoke per variant.
- Manual DEMO3 results versus prior 11.78 FPS experimental and complete
  PLAY functionality.

## Next genuine runtime milestone

Implement an exclusive framebuffer/VDP owner (M3) with safe retirement
of prior 8×8 DMA/ISR readers and a real pixel4 geometry frame producer,
then texture/sky/HUD handling. P2I's host preview is only a preparatory
path; it is not presented or uploaded by the Mega Drive yet.
