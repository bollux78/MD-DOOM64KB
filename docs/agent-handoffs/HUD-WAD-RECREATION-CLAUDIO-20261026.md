# HUD-WAD: Doom status bar recreated from the IWAD (Cláudio, 2026-10-26)

Branch `exp-claudio-hud-wad-20261026` (from R66 `f5a9daa`). Workflow run 40396752797: all steps green.

## What it is
The original STBAR/face/digit/arms/key graphics are read from the IWAD **at build time on the runner** (`scripts/lab/gen_hud_wad.py` -> `src/hud_wad_assets.h`, gitignored; the WAD is never committed).
Approximation allowed by the user: STBAR squeezed 320->256 px (area average), one 15-colour + black palette (CRAM line 3), 9-bit MD colours.
Flag `-DDOOM_HUD_WAD` (off = ROM byte-identical to approved R66; verified by `cmp` against run 40231459814).

## Design
- 32x4-cell bar on BG_A rows 22..25 (H32 x0=3, H40 x0=4), palette 3, priority high; tiles at VRAM 800.. (+12-tile face slot).
- Big 8x16 digits for ammo/health/armor, small digits for the 4-ammo table and ARMS, keys, 3x4-cell face.
- Face = port of `ST_updateFaceWidget` (dead, evil grin, attacked/ouch, rage, god, idle random), run per tic from `ST_Ticker`.
- Redraw only when an 8-bit digest of the displayed numbers changes, plus a forced redraw every 32 tics (bounds digest collisions). Face tiles uploaded only on face change.
- BSS: HudFace 6 B + digest 1 B (packed; R66 play control had only 12 B margin).

## Results (run 40396752797)
| variant | BSS | margin |
|---|---:|---:|
| r66-control | 57900 | +20 |
| r66-play-control | 57908 | +12 |
| r66-hud-perf | 57908 | +12 |
| r66-hud-play | 57918 | +2 |

HUD BSS cost: PERF +8 B, PLAY +10 B. Timedemo (BlastEm, 2133 tics): 3D pixels IDENTICAL to control; HUD-perf +0.36 % vblanks (noise level, measured with the bar drawn).

## Limits / not validated
- Not seen running by me (only a host-rendered preview PNG in artifact `doom-md-hud-wad`); visual validation is the maintainer's.
- No skull keys (port has 3 cards); labels are squeezed; palette flashes do not tint CRAM line 3; H40 has 4 black columns each side.
- Margin of 2 B on `r66-hud-play`: any further BSS growth needs a trade-off.

## Use
Play: `doom-md-r60-r66-hud-play.bin`; timing: `doom-md-r60-r66-hud-perf.bin` (artifact `doom-md-hud-wad`, dist/hud/).
