# R11 topleftclip — black top row + left column, based on R10 Dist

User confirmed two additional identical DEMO3 runs: R11 topclip 9.90 FPS (215.58 s), topdma 9.89 FPS (215.67 s). The latter loses slightly, so disable its row0 DMA comparison. New request: avoid rendering the leftmost 3D column x=0, creating a visually balanced black left edge beside the already-black right margin, while preserving the R10 Dist arithmetic path and R11 topclip.

## Implementation
- Keep physical 38x24 3D tile buffer and 38x28 including HUD; no 37-wide stride, rescale, or camera shift.
- At R_ClearClipSegs mark solidcol[0]=1; R_ClipWallSegment skips the column and R_CheckBBox treats it as occluded. This skips wall texture calculations at x0, not just the final tile write.
- World sprite and player weapon projection clamp vis->x1 to 1 (rather than 0), preserving existing vis->startfrac compensation so texture sampling remains aligned. Reject sprites whose x2<1.
- Automap Bresenham plotting omits x0 in GS_LEVEL.
- On entry to a level, clear x0 for rows y=1..23, as well as the top bar y0. The top bar can still show FPS and future messages; bottom HUD unaffected.
- Keep DOOM_R11_TOPBAR_CLIP=1 and DOOM_R11_TOPBAR_DMA=0. R10 reciprocal is disabled. R9 Slope, R9 Step and R10 Dist remain enabled.
- Effective world tile area x1..37, y1..23 => 851 tiles, compared to original 912 tiles, saving 61 visible cells in total (38 top row + 23 left column). This does NOT imply proportional FPS improvement.

## ROMs
- `doom-md-hud-r11-topclip.bin` — identical flags to prior validated 9.90 FPS control.
- `doom-md-hud-r11-topleftclip.bin` — same plus DOOM_R11_LEFTCOL_CLIP.

## Validation
The build script checks compiler flags, ROM headers, ELF and logs; static test checks clipping, texture sampling and simulated clip ranges. Run DEMO3 NTSC 60 Hz 2134 frames in BlastEm divider 7, compare times, inspect gameplay for black left/top borders and weapon/world sprite clipping. Then test winner on real Mega Drive 7.67 MHz. Do not assume this is stable merely because it compiles.
