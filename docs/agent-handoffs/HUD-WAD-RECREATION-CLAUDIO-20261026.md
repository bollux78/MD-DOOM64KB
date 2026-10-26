# HUD-WAD: Doom status bar recreated from the IWAD (Cláudio, 2026-10-26)

Branch `exp-claudio-hud-wad-20261026` (from R66 `f5a9daa`). Workflow run 40396752797: all steps green.

## What it is
The original STBAR/face/digit/arms/key graphics are read from the IWAD **at build time on the runner** (`scripts/lab/gen_hud_wad.py` -> `src/hud_wad_assets.h`, gitignored; the WAD is never committed).
Approximation allowed by the user: STBAR squeezed 320->256 px (area average), one 15-colour + black palette (CRAM line 3), 9-bit MD colours.
Flag `-DDOOM_HUD_WAD` (off = ROM byte-identical to approved R66; verified by `cmp` against run 40231459814).

## Design (final, approved by the maintainer 2026-10-26 19:20)
- Source: the runner IWAD only (STBAR + STARMS plate, STTNUM/STYSNUM/STGNUM, STKEYS, STF* faces); nothing derived is committed.
- Background: STBAR+STARMS squeezed 320->256 px, one 15-colour MD palette (CRAM line 3), **Floyd-Steinberg 100 %**. Faces: own 15-colour palette (CRAM line 2), Floyd-Steinberg from the original patches, centred in a **4x4-tile black square**, 2 px down so the top frame stays.
- Big digits are transparent over the original bar: one tile per (widget, position, tile row, digit), drawn 4 px lower. ARMS digits are centred in the plate boxes; key cards and ARMS digits are boolean tile variants over the real bar cells. The ammo table uses small digits over a stone tile per row (BULL/SHEL labels are not kept).
- Face = port of ST_updateFaceWidget (per tic from ST_Ticker). Redraw only when an 8-bit digest changes + forced redraw every 32 tics. State: HudFace 6 B + digest 1 B.
- Real IWAD: 390 static tiles + 16 face-slot tiles (free VRAM range allows 640); ROM +~12 KB; no extra BSS.

## Results
R66 (run 40410981556) and R70-A12 (run 40410986634), all steps green, control ROM byte-identical to the approved one, 3D pixels IDENTICAL over 2133 tics.
| variant | BSS | margin |
|---|---:|---:|
| control perf (r66 / a12) | 57900 | +20 |
| control play | 57908 | +12 |
| hud-perf | 57912 | +8 |
| hud-play | 57918 | +2 |
Timedemo, HUD-perf vs control: +0.38 % vblanks on both bases (noise level, bar drawn).

## Limits / not validated
- Not seen running by me (only host-rendered previews); visual validation is the maintainer's.
- No skull keys (3 cards); labels of the ammo table dropped; palette flashes do not tint CRAM lines 2/3; H40 has black margins.
- Margin of 2 B on hud-play: any further BSS growth needs a trade-off.

## Use
R66: branch `exp-claudio-hud-wad-20261026`, artifact `doom-md-hud-wad`, play ROM `doom-md-r60-r66-hud-play.bin`.
R70-A12: branch `exp-claudio-hud-r70a12-20261026`, artifact `doom-md-hud-r70a12`, play ROM `doom-md-r60-r70a12-hud-play.bin` (also a12 perf / play controls and hud-perf).
