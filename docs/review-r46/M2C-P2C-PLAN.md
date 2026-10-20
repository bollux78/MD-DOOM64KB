# R46 M2C/P2C — sprite rectangle projection contract (76x44)

**Base approved by user:** M2C/P2B (three ROMs functional). DEMO3 control 11.80 FPS/180.82 s; experimental 11.78 FPS/181.12 s. Treat 0.30 s difference as measurement to track, not zero regression.

This checkpoint provides pure, self-contained camera-space sprite bounding rectangle projection with fixed-point inputs and clamping to 76x44. Source uses 64-bit intermediates for arithmetic safety. The computational cost will require benchmarking before use on the active 68000 draw loop. Caller supplies output, with rejected projections leaving it unchanged.

**Not present yet:** world-to-camera rotation, actor/patch selection, depth sorting, texture sampling, masked columns, or actual rendering at 4x4. No framebuffer owner or live resolution toggle. Existing 8x8 renderer remains untouched. Test all three ROMs and the P2B performance difference.
