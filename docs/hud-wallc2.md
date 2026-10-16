# HUD24 C2 — Direct ROM tangent lookup

Target: optimize the `R_RenderSegLoop()` wall texture-column geometry
without any assembly renderer code.

## Baseline

The known-good HUD24 status-only DMA build completes DEMO3
(2134 frames, BlastEm NTSC, 68000 divider 7) at **9.39 FPS**.

Round W1 tested inline wall pixel ASM but measured 9.38 FPS versus
9.39 FPS in C, so PR #16 was closed without merge.

## Single proposed change

The existing C code chooses between four tangent-table quadrants
per textured screen column, then computes `rw_distance * tangent`
and applies the signed correction to `texturecolumn`.

Experimental C variant introduces one direct 4096-index ROM lookup.
The table is **generated from existing exact `finetangentTable_part_3/4`
constants in `src/r_draw.c`**, not recalculated with floating point.

No angular interpolation, cache modification, HUD/VDP change, altered
viewport, SRAM requirement, or reordering of signed rounding.

- New ROM table: 4096 × `fixed_t` = **16,384 bytes of ROM**.
- No new runtime WRAM array. The generated source header is untracked.
- Angles outside 0..4095 retain the original four-branch behavior.
- **C baseline** builds from same branch, macro disabled.
- **LUT experiment** builds with `DOOM_WALL_TAN_LUT=1`.

Build two PERF ROMs:

```fish
cd ~/Projetos
git clone --branch exp/68k-hud24-walltan-c-round2 \
  https://github.com/bollux78/MD-DOOM64KB.git doom-md-hud-wallc2
cd doom-md-hud-wallc2
fish scripts/lab/run_hud_wallc2.fish
```

Generated ROMs in `dist/hud-wallc2/`:

- `doom-md-wallc2-c-perf.bin`
- `doom-md-wallc2-lut-perf.bin`

Run C control first. If it passes all 2134 frames, run LUT and confirm
correct wall texture mapping, correct HUD and 2134 frames. Report both
FPS and elapsed time. If the LUT is slower, discard the change.

**Not compiled or runtime validated by assistant**. Do not merge or
test experimental ROM on real cartridge before emulator completion.
