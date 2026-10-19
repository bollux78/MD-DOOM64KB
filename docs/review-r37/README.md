# R37 — Live BSP / render-work profiling on R35d 8x8

This branch is based on the **tested 8x8 R35d checkerboard**, NOT the slow 4x4 Pixel4 experiment.
All music (XGM2), 52 PCM sounds, native graphics, save SRAM, map selection and controller mapping remain enabled.

## ROMs

- `doom-md-r37-cell-play.bin`: live diagnostic overlay (extra CPU and HUD DMA cost).
- `doom-md-r37-cell-perf.bin`: uninstrumented R35d timedemo control, intended to match its 11.16 FPS DEMO3 baseline.

## The 12 live metrics

During gameplay, the first row just below the 3D image and two rows beneath the HEALTH/ARMOR/AMMO HUD show:

| HUD | Meaning | Where incremented |
|---|---|---|
| N | BSP internal nodes visited | iterative R_RenderBSPNode |
| B | back-subtree bounding boxes tested | R_CheckBBox |
| V | bounding boxes rejected outside FOV or with zero visible column width | R_CheckBBox |
| O | bounding boxes fully hidden by nearer solid wall columns | R_CheckBBox |
| S | BSP subsectors visited | R_Subsector |
| G | segment candidates evaluated | every R_AddLine call from R_Subsector |
| E | segments rejected early: backface, FOV or projected zero width | R_AddLine |
| W | unoccluded wall fragments sent to R_StoreWallRange | R_ClipWallSegment |
| C | iterations of the per-column R_RenderSegLoop | R_RenderSegLoop |
| F | visible floor/ceiling column runs (not individual pixels) | R_RenderSegLoop |
| T | textured column writer calls for walls and masked/sprite textures | R_DrawColumnSprite |
| K | visible sky column runs | R_RenderSegLoop |

Rows show **four decimal digits per metric**. They are reset once per rendered 3D frame and updated after drawing, with HUD DMA forced each frame for profiling only. These are **work counts, not CPU cycle or millisecond measurements**. No magic framebuffer/offscreen visibility inference is made.

The instrumentation intentionally has nonzero CPU/RAM/VDP overhead. **Compare event counts between view angles**, and compare normal FPS on the clean control `cell-perf`, not live-profiling FPS directly with a normal ROM.

## Hardware test protocol: E1M1 final room

1. Use `doom-md-r37-cell-play.bin` on the Mega Drive or BlastEm and select E1M1.
2. Reach the small square room at the end, stand still and face a wall that used to show high FPS (>20 in uninstrumented R35d). Take a photo/screenshot including all three diagnostic rows, the FPS counter, and the game image.
3. Turn to the wall that previously showed ~11–12 FPS, stay in the same position, and send a second image of the counters.
4. Optionally face each of the four walls to provide four comparisons, avoiding moving forward/back to keep BSP viewpoint consistent.
5. Run `doom-md-r37-cell-perf.bin` separately to verify the normal DEMO3 control remains around the known 11.16 FPS average.

Interpretation:
- High N/B/S/G with low W/C/T implies excess geometric traversal/visibility checks.
- Similar N/B/S/G but much higher W/C/F/T implies wall, flat or texture writing dominates.
- High B with low O points to ineffective wall occlusion or frustum checks; high O shows back subtrees being correctly discarded.

Future optimization should change **one algorithm per build**, preserve visual output and map/gameplay stability, and validate DEMO3 timing against the clean R35d control.
