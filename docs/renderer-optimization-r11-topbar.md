# R11 — dedicated black top tile row, without altering 38x24 projection

The user proposed turning the first tile row, which already carries the FPS counter, into a permanent black telemetry bar, rendering only the 23 rows beneath it and keeping the four bottom text HUD rows.

## Geometry and correctness

- Preserve `VIEWWINDOWWIDTH=38`, `VIEWWINDOWHEIGHT=24`, `VDP_DISPLAY_ROWS=28` and all projection tables. Do **not** change the center of projection, crop or rescale the remaining view.
- At the start of the level's wall rendering, initialize `ceilingclip[x]=0` instead of -1. All wall/sky/floor clipping starts at y=1.
- Masked sprites and player weapon sprites use independent -1 clipping arrays: additionally clamp `yl>=1` in `R_DrawMaskedColumn`. Otherwise sprites could overwrite the black bar.
- Automap drawing via `V_DrawLine` skips row 0 when in-level. Top row still accepts text messages from `HU_Drawer` and FPS from `I_DrawDebugCounters`.
- Clear the top bar on entry to level, leaving existing title/menus unchanged outside `GS_LEVEL`.

## DMA

- The existing HUD-status-only DMA sends rows 0..23 unless health/armor/ammo changes, when it sends rows 0..27.
- Optional R11 DMA optimization compares the actual 38 top-row tile words to a snapshot. When unchanged and in-level, DMA only rows 1..23, or 1..27 when the bottom HUD changes. On changed FPS, messages, automap, or state transitions, send row 0 as well.
- Avoid separate VDP writes or additional DMA calls; retain one contiguous DMA per frame.
- Skip 38 tile words (76 bytes) per frame in the common case. That does not imply a 4.17% FPS improvement because geometry, logic, and other rows still execute.

## Three benchmark ROMs

| ROM | Reference / change |
|---|---|
| `doom-md-hud-r11-base.bin` | R10 Dist baseline, no R11 changes; expected 9.85 FPS in BlastEm |
| `doom-md-hud-r11-topclip.bin` | black top bar; wall, sky, sprite, weapon and automap row0 clipping, original DMA |
| `doom-md-hud-r11-topdma.bin` | topclip plus unchanged-row0 DMA omission |

R9 slope and scale optimizations and R10 Dist are enabled in all three. R10 reciprocal optimization is disabled, because it had no benefit and the R10 Combined version crashed in BlastEm. All ROMs are uninstrumented and preserve 7.67 MHz target.

## Acceptance

BlastEm stock divider 7, NTSC60, DEMO3 2134 frames, no crashes or graphical artifacts; verify the top bar remains black except for FPS/messages, that sky and sprite pixels never reach y0, and that automap/menus/telemetry refresh. Repeat any FPS winner and then test on real Mega Drive 7.67 MHz.
