# R76 — A2/L3/HN color choice + blue-biased hybrid + persistent menu overlay

**Data:** 27/10/2026  
**Branch:** `exp-chatgpt-r76-color-choice-20261027`  
**Status:** code committed and runner workflow created; binary success/hardware QA require independent confirmation. No claim of performance gains.

## Hardware observations behind this iteration

- L3 generally offers the sharper walls and several gray/olive sky-floor combinations.
- HN offers better color in particular olive/green flat regions.
- A2 wins on blue floor and strongly red enemies.
- Start menu over gameplay still flickers in its upper “DOOM” / “Select Level” area in R75, while the menu item list and static-title menus are stable.
- The user-provided mosaics cover slightly differing screenshot frames in BlastEm; compare real hardware in the same game position.

## Solution

A single PLAY ROM offers **four selectable FULL color profiles** in Options:

1. **Hybrid Blue** (default): L3 CRAM+walls+sprites and original M50 checker. Flats otherwise follow HN, but strong-blue source colors use an A2-targeted map constrained by L3 CRAM. Approximation, not guaranteed blue match.
2. **A2 Full**: full N25A-M50/allow palette and wall/sprite LUT, F2 flat LUT. This is the option that can display the exact A2 palette colors, including red enemies.
3. **L3 Detail**: full L32F-M50/forbid palette and wall/sprite LUT with F3 flats.
4. **HN Smooth**: L32F-M50 full palette + HN flat LUT, retaining L3 wall/sprite details.

The selector changes **both 16-color CRAM banks, M50 physical pair-tile patterns and wall/flat/composed LUT pointers** through the existing R59 machinery. The selected mode is visible in Options; heavy reload happens only after the menu closes, to avoid blanking its header while browsing. No cross-profile CRAM palette overlay is attempted.

A2/HN/L3 are regenerated from the pinned source WAD and existing R52/R53/R74/R75 generators. Exact byte equality to historical R53 ROMs is not asserted; the generator self-test checks that every mode preserves its own regenerated inputs byte-for-byte.

## Menu flicker change

R75 already skips 3D presentation while PLAY Start menu is open. However `R22_Text()` still called `R22_ClearOverlay()` on each new frame, clearing WINDOW and BG_B tilemaps repeatedly via DMA, which can blink upper glyphs.

R76 adds an experimental *persistent menu overlay*:
- Reuse R40b's existing 105-byte `prev` + 105-byte `seen` occupancy bitsets aliased to the frozen Pair-V framebuffer (zero additional BSS).
- Clear full WINDOW/BG_B only once on menu entry.
- Keep glyphs rendered into WINDOW on subsequent menu frames.
- At end of M_Drawer, clear only glyph tilemap cells that existed last frame and were not redrawn.
- On menu exit, normal R22_EndOverlay retires the window and the game redraws on the next gameplay frame.
- In PERF, where rendering does not freeze on menu, this alias optimization is disabled.

This is an experimental fix, not yet hardware verified. Confirm text and selector remain stable during Start → Select Level → Options → Back → Resume, plus scrolling and native title screens.

## Build / artifacts

Workflow: `.github/workflows/r76-color-choice.yml` on the self-hosted runner.

Two variants:
- `doom-md-r60-r76-col-pl.bin` — PLAY, HUD-WAD, menu system and runtime palette chooser.
- `doom-md-r60-r76-col-pf.bin` — PERF, DEMO3 clock-original benchmark.

Expected artifact: `doom-md-r76-color-choice-2-roms`.

Build verifies SHA-256, ROM <= 4MiB, BSS <=57,920, all mandatory flags, N25A/L32F CRAM and codebooks versus generated source and four mode labels. Original R71A12MUL-HUD baseline preserved.

## Suggested test procedure

First launch PLAY with **Hybrid Blue**. At the same positions from R75 mosaics:
- Strong blue floors: compare Hybrid Blue vs **A2 Full**.
- Red enemies: compare with **A2 Full** (only it preserves A2 CRAM).
- Gray/olive flats: compare Hybrid Blue vs **HN Smooth**.
- Wall details and strong grays: compare **L3 Detail**.
- Pause menu Start: wait several seconds, switch submenus and selector, then return to the game; inspect upper title and old cursor remnants.
- Verify HUD intact through damage and menus, no sudden large mosaic/tearing.

Then PERF DEMO3 clock-original; FPS is measured by total frames / elapsed seconds, not an instantaneous 30fps snapshot.

## Remaining architecture limit

With shared PAL0 and PAL1 and the Pair-V tile codebook, pixel-by-pixel mixing A2 saturated reds and L3 detailed walls inside the same frame is **not equivalent** to runtime mode switching. A2 colors cannot be introduced into the L3 palette by changing LUT indices alone. A future hybrid CRAM synthesis or hardware-palette split would need separate VRAM/palette budgeting and regression tests.
