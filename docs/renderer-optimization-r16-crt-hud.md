# R16 — CRT overscan: move HUD up 2 tile rows, preserve the weapon

## Evidence and baseline

On original Mega Drive 7.67 MHz with CRT, R15 **setupu** completed DEMO3: **10.04 FPS, 212.48 s, 2134 frames**, without crashes. The CRT overscan hides some of the HUD text at the bottom. The emulator result was 10.16 FPS / 210.03 s. Do not assume emulator and CRT timings are identical.

## Implementation

- Keep the original R15 setupu optimization, 38-column symmetric image, clipped top telemetry row, left border, 16 cache slots, and 65535-entry R12 reciprocal LUT.
- Raise the HUD exactly **2 tile rows = 16 pixels**. Old HUD values row 25 and title row 27; new values row 23 and title row 25. The black rows 26–27 protect the HUD from CRT overscan.
- Use **actual 38x22 renderer** for R16 instead of rendering 38x24 then hiding its bottom two rows. This recomputes `CENTERY`, perspective, sprite scale, wall and sprite clip arrays, so the weapon is not arbitrarily cut by an overlay.
- Keep VDP tilemap DMA height 28 on HUD changes and 22 on unchanged HUD; the last two rows are always black in the 28-row RAM buffer and initialized in VDP on a changed HUD.
- Optionally move only the **first-person weapon** upward 1 or 2 tile rows by adjusting its `vis->texturemid`. This moves the sprite's geometry and texture sampling consistently; world sprites are unaffected. Weapon scale is recomputed for the 22-row viewport.
- Keep menus/fullscreen and automap drawing bounded by the new viewport, not by the 28-row VDP buffer.

| ROM | Viewport | HUD text rows | Weapon |
|---|---|---|---|
| r16-control | 38x24 | 25 and 27 | unchanged R15 setupu |
| r16-up2 | 38x22 | 23 and 25 | normal recalculated scale |
| r16-hand1 | 38x22 | 23 and 25 | lifted one tile row |
| r16-hand2 | 38x22 | 23 and 25 | lifted two tile rows |

**Benchmark:** BlastEm NTSC 60 Hz, 68000 divider 7, DEMO3 2134 frames. **Visual CRT test:** check visibility of HEALTH/ARMOR/BULLETS and the bottom title, hand/weapon while idle and firing, clipping of walls and sprites, and game transitions. Do not promote any variant until stable on real hardware.

If weapon looks too high, prefer `up2`; if bottom of the hand is cut, compare `hand1` and `hand2`. Repeated measurements are needed before attributing a small FPS change to code.
