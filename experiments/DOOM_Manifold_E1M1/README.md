# Manifold E1M1 — M01 (isolated research branch)

**Status (2026-11-10): M02 ROM builds, boots and is walkable in MAME and BlastEm (headless). Physical console: NOT TESTED.**

## Download (stable URL)

Latest ROM: https://github.com/bollux78/MD-DOOM64KB/releases/tag/manifold-e1m1-latest

Direct file: `https://github.com/bollux78/MD-DOOM64KB/releases/download/manifold-e1m1-latest/doom-md-manifold-e1m1-m02-hintfix.bin`

The tag is moved to the newest successful build; the release notes carry the build commit, run link and SHA-256. Open the `.bin` in BlastEm (or any Mega Drive emulator / flash cart). Press START to enter the map; D-pad moves/turns.

### What works / what does not (M02)
- Works: boot without ADDRESS ERROR, E1M1 geometry as portal cells, walking and turning, ~6-12 fps in the start room (control ROM ~20 fps).
- Missing: HUD weapon sprite, WAD textures (flat colours), THINGS (monsters/items), doors/triggers, real PVS. Some ceiling clipping artifacts at certain angles. 112 unpaired BSP edges are kept as solid walls.
- Verified only in emulators; behaviour on real hardware is unknown.

### Licensing / provenance
- Renderer: Manifold by ehaliewicz (MIT), pinned commit `b6fe52a`; built with SGDK 2.11 (MIT).
- The map is converted from E1M1 of the Doom **shareware** `doom1.wad` (id Software). The ROM contains derived level geometry only, no WAD textures, sprites or sound. Doom's data remains id Software's/ZeniMax's; this experiment is unofficial and non-commercial.

Handoff with root causes and diagnostics: `docs/agent-handoffs/MANIFOLD-E1M1-M02-PLAYABLE-CLAUDE.md`.

Goal: make the **actual Doom E1M1 geometry** render in Manifold's Sega Mega Drive portal renderer, with honest pixel/time comparison to R128. The existing R128 and Sega CD M1.5 remain untouched.

## Evidence checked against original Manifold
- Original source: https://github.com/ehaliewicz/Manifold
- Pinned commit: `b6fe52a52344464de00bde4dc58a40f8b89cfc1a`
- License: MIT (retain copyright and license when redistributing derivatives).
- Main renderer files: `src/portal.c`, `src/bunch_render.c`, `src/draw.c`, `src/my_bmp.c`.
- A substantial generated Doom E1M1 dataset exists in `src/python/e1m1.c` (including Things, BSP-related arrays).
- **Crucial:** original `src/map_table.c` registers only `overlapping_map`, `editor_test_map`, `building_test_map`. `src/maps.h` does not include an E1M1 map. The generated `e1m1.c` is not automatically playable. Manifold uses its own convex-sector `portal_map` runtime representation, and Doom E1M1 must be converted/adapted. Do not simply append `&e1m1` to the table.
- Original `src/python/editor/wad.py` reads a custom **BWAD** file, not a Doom IWAD; use our *existing* Doom WAD parsers or an explicit IWAD importer for source geometry.
- Original `src/my_bmp.c` documents a column framebuffer / staggered DMA; this is a promising test target, not a measured speedup.

## M01 progress update — 2026-11-09

- Real E1M1 (pinned Doom shareware WAD): 237 subsectors, 732 original segs, 467 original vertices. Original SSECTORS alone leave 182 open boundaries.
- Rebuilding cells from BSP NODES yields 237 closed convex cells with zero degenerate areas. A further strict audit found 14 SEG midpoint disagreements (threshold 0.75 geometric sign units); updated code now measures normalized deviations in map units. This is not yet approved topology.
- First C portal_map candidate requires 1112 atomic wall pieces after splitting, above Manifold's 1024 static budget. Experimental-only limit raised to 2048.
- Added guarded `emit_portal_map.py`, `stage_rom.py`, and `manifold-e1m1-rom.yml`. The pipeline stages the real spawn point, registers the E1M1 map, and attempts compilation with the locally installed SGDK into the runner's private directory.
- **No playable Manifold E1M1 ROM has passed build or BlastEm yet**. Check the latest `Manifold E1M1 M01 experimental ROM` run before using any generated file. Current structural placeholders: one common wall texture, conservative PVS/PHS, no objects, door scripting pending.
- Original Doom R128 / SCD M1.5 branches are unaffected.

## First technical milestones

1. M01-A: stage pinned upstream in a **disposable directory**, inventory map and renderer dependencies, and record source provenance. Script: `m01/bootstrap.py`. It creates `audit.json` and deliberately does NOT certify or compile a ROM.
2. M01-B: write a Doom E1M1 -> Manifold `portal_map` converter: load VERTEXES, LINEDEFS, SIDEDEFS, SECTORS, SEGS/SSECTORS/NODES and THINGS; build convex cells and portal adjacency; preserve linedef textures, floor/ceiling heights, sector lighting and door semantics. Check limits `MAX_SECTORS`, `MAX_WALLS`, `MAX_VERTEXES`, `MAX_PORTALS` before generating C. Conversion needs its own geometry/portal tests, including door closed/open state and partially occluded actors.
3. M01-C: compile a **standalone Manifold ROM** using pinned upstream and the converter; present static E1M1 spawn camera first, then movement and correct sector transitions.
4. M01-D: compare frozen-camera views and measure raster, copy/DMA and total display time, using the same viewpoint, resolution, palette policy and texture detail as R128. Run automated build and BlastEm; retain explicit `build: PASS/FAIL` and `blastem: PASS/FAIL`.
5. M01-E: only if promising, test full sprites/doors and then Sega CD logic compatibility. No rendering changes in current SCD M1.5 branch.

## Run the current bootstrap

```bash
python3 experiments/DOOM_Manifold_E1M1/m01/bootstrap.py --out /tmp/manifold-e1m1-m01
```

Network access to GitHub and git required unless `--source /path/to/Manifold` is specified.
Do not put private WADs, generated copyrighted assets, ROM binaries, or private machine paths in commits. R128 builds, runners and M1.5 remain isolated.

## Acceptance gate
No performance claims until equivalent images and independent timings exist. No accepted release without both build and BlastEm passing. Hardware testing is a separate additional gate.

## VRAM map (M04, SGDK 2.12 layout with 64x64 planes)

| VRAM | Use |
|---|---|
| 0x0000-0x01FF | SGDK system tiles (16) |
| 0x0200-0x71FF | 3D framebuffer tiles, double buffered (896 tiles, 28 KB) |
| 0x7200-0x9BFF | HUD, inventory, weapon sprites, console (~300 tiles) |
| 0x9C00-0xA7FF | SGDK font (96 tiles) |
| 0xA800 / 0xAC00 | H-scroll table / sprite list |
| 0xB000-0xBFFF | **reclaimed**: WINDOW nametable is unused -> sky tiles (128) |
| 0xC000-0xCDFF | BG_B rows 0-27 (HUD + sky tilemap) |
| 0xCE00-0xDFFF | **reclaimed**: BG_B rows 28-63, never displayed -> sky tiles (144) |
| 0xE000-0xFFFF | BG_A 64x64 = the two framebuffer tilemaps (vertical-scroll flip) |

Enemies/objects are rasterised into the software framebuffer, so they cost no VRAM.
