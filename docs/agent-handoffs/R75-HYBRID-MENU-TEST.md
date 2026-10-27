# R75 — hybrid A2 flats + L3 walls, and Start menu no-flicker test

**Date:** 2026-10-27. **Status:** source/workflow published; compilation success and real hardware visual/flicker results NOT yet confirmed.

## User feedback

- User-selected favorites: **A2 flats** (N25A-M50 F2) and **L3 walls** (L32F-M50 F3).
- Four images in the latest composite are labelled A1/L3/A1/L3; treat these image labels separately from the user's explicit A2 request.
- Flicker appears when entering Start menu over active gameplay; menus over static title screens have no such issue.
- Shared CRAM means copying A2 flat indices directly into L3 cannot preserve A2 color. The R75 hybrids are *approximations* constrained to the actual L3 hardware palette, not an exact overlay of independent palettes.

## Build matrix (all mandatory HUD / R71 MUL ASM / M50 physical checker / H40)

| Variant | Engine palette + walls | Flat LUT | Menu |
| --- | --- | --- | --- |
| r75-a2-pf/pl | N25A | A2 F2 | Freeze 3D, hold last VRAM |
| r75-l3-pf/pl | L32F | L3 F3 | Same |
| r75-h2-pf/pl | L32F | R75 A2-targeted: favor matching A2 perceptual flat result | Same |
| r75-hn-pf/pl | L32F | R75 A2-targeted: favor smaller even/odd differences | Same |

**Testing order:** a2-pl, l3-pl, h2-pl, hn-pl; PERF variants for DEMO3. Same screenshots/camera/NTSC real hardware clock.

## Implementation details

- `scripts/lab/gen_r75_hybrid.py` recreates the A2 F2 LUTs and M50 companions using the existing generators in a separate directory, then compares the *effective* A2 flat colors against candidate L3 flat-only pairs. It emits two static 256-byte flat mappings for the L3 CRAM. No new CPU calculation per pixel.
- `scripts/lab/inject_r75_hybrid.py` changes ONLY the flat even/odd aliases in the selected R59-mode-zero codebook. L3 wall maps, composed wall LUTs, CRAM and companions remain as in L3.
- `scripts/lab/apply_r75.py` generates eight isolated ROMs. Mandatory HUD retained.
- The `DOOM_R75_MENU_HOLD` patch is in `src/d_main.c` in the disposable checkout. While the menu is open in gameplay, M_Drawer performs its VDP glyph overlay writes, but the engine does not queue an empty Pair-V framebuffer DMA via `I_FinishUpdate()`. Closing menu resumes rendering and normal presentation. Check that menu glyphs render properly and are cleaned when closed; verify START/OPTIONS/RESUME and title-screen unaffected.

**Alternative, not implemented in this round:** runtime A2/L3 profile switching in Options. It would require coordinated switching of *both* CRAM palettes, 512 pair tiles, wall/flat composed LUTs, pending DMA, menus and native-art exit. It is not safe to implement by changing a mode byte alone; prioritize fixed-palette hybrids first.

## Verification

Workflow: `.github/workflows/r75-hybrid-menu.yml`; self-hosted runner, eight ROMs, ELF, flags, sha, manifest, per-ROM R74 flat report and per-hybrid R75 report. ROM <=4 MiB, BSS <=57920, all eight must include HUD-WAD and menu-hold flag.

**Acceptance:** homogeneous blue floor comparable to A2, wall definition comparable to L3, no coarse checker, game HUD preserved, no Start-menu flicker, DEMO3 FPS measured vs matching controls. Failure of any claim requires new fixes, not a declared success.
