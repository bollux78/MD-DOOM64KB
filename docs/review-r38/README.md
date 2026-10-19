# R38 — measured CPU stage shares for Doom Mega Drive R35d (8x8)

This is a **diagnostic experiment**, based on the proven R35d 8x8 checkerboard renderer.
No changes to BSP rejection logic, on-screen rendering, SRAM, music, SFX or map data.

## Three builds

- `doom-md-r38-cell-play.bin` — playable 8x8 renderer with a live HUD showing exclusive sampled CPU-stage percentages.
- `doom-md-r38-cell-perf.bin` — **clean** uninstrumented R35d DEMO3 reference, expected ~**11.16 average FPS**; do not conflate with instrumented play.
- `doom-md-r38-cell-profperf.bin` — DEMO3 benchmark with profiling enabled throughout the demo, showing 11 sampled percentages on its result screen. This one's FPS includes profiling overhead.

The timer samples the *main CPU stage interrupted by each VBlank* at NTSC 60 Hz (in I_VBlankCallback).
**Time shares are statistical estimates over many interrupt samples, not cycle-accurate CPU timings.**
Total samples normally sum to 100% across the 11 exclusive categories. Stage 5 covers main-thread VDP
presentation/queue wait, **not** separately measured ISR DMA duration; VBlank ISR overhead isn't assigned
as its own category. The source is the existing R7 profiling stage instrumentation, enabled in PLAY
without the legacy DOOM_ROUTINE_PROFILE switch (which otherwise forces timedemo).

## HUD legend

While playing, the diagnostic shows three text rows around the normal HEALTH/ARMOR/BULLETS HUD:

| Mark | CPU work sampled |
|---|---|
| **L** | Doom logic/other outside the renderer |
| **P** | Frame setup, buffer clears |
| **B** | BSP traversal and subsector work excluding its separately timed nested calls |
| **C** | Remaining wall-column loop work: clipping, scaling, flat span decisions, texture calculations |
| **M** | Masked walls, sprites, weapon render |
| **D** | Presentation, frame pacing / DMA queue wait on main 68k thread |
| **W** | Actual textured wall-column drawing |
| **X** | Multi-patch column composition |
| **R** | Wall-range setup and clipping not charged to nested column loop |
| **A** | R_AddLine visibility/segment logic |
| **O** | R_CheckBBox / bounding box checks |
| **Q** | Count of 60Hz samples used, **not** time percentage (up to 600) |

A display of `W 023.4` means about 23.4% of the observed time falls within that exclusive routine.
Profile rows appear at HUD offsets +0, +2, +3; the player status remains on row +1.
The screen refreshes the profiler once per 60 new samples (about one second), not every frame,
limiting diagnostic DMA overhead. It updates immediately on a camera turn/reset.

Each new view angle or player position automatically clears samples. Stay **absolutely still for
ten seconds** after rotating, until `Q 0600`. At that point, the display freezes until movement.
This makes all directions comparable at the same accumulation duration.

## Capture protocol

1. In the small square **E1M1 exit room**, stand in the middle. Record 4 screenshots after Q=600:
   facing exit button, facing entry door, back to button, back to door.
2. In the **E1M1 start**, stand still at spawn. Record 4 screenshots after Q=600:
   default view, 90 degrees right, 180 degrees, 90 degrees left.
3. Send those shots. We'll compare relative stages with the already-collected **R37 BSP work
   counters** for the same 8 directions (do **not** infer CPU time from raw BSP counts alone).
4. Run `cell-perf` for control and `cell-profperf` for whole-DEMO3 stage distribution.
   The profperf results use split columns and intentionally disable R28 video-audit overlays
   to keep the sample-percentage report legible.

## Optimization decision criteria

- If **B + A + O + R** is high in the expensive direction, consider BSP and visibility tests.
- If **C + W + X** dominates, optimize textured wall setup, lookups, or per-column assembly.
- If many **F** (R37 flats) appear but **C** dominates, investigate flat drawing / wall-loop
  work (R38 C includes floor/ceiling pixel decisions in the wall-column loop).
- If **D** dominates, measure VDP present queue synchronization and avoid extra DMA.
- If **M** dominates in sprite-heavy directions, target masked sprites only.

Keep exact 8x8 artwork, 169/256 checkerboard shades, 52 PCM samples, XGM2 and save/load behavior.
Apply one optimization at a time, compare its **uninstrumented** DEMO3 average FPS to 11.16,
run the same R37/R38 capture viewpoints, and visually inspect correctness.

## Known limitations

- 60 Hz VBlank sampling has discretization noise; 600 samples yields useful directional
  proportions, not microsecond-level latency.
- Short rare routines (e.g. small bounding-box tests) can be statistically underrepresented.
- Instrumentation adds minor CPU/memory cost. No change to the normal renderer is implied by
  an instrumented FPS difference.
- Profiles are relative time shares. The absolute per-stage duration requires additional
  timing hardware/instrumentation or combining stage shares with average frame duration.
