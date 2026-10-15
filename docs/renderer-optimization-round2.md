# DOOM MD — Renderer optimization, Round 2

## Controlled experiment

All variants keep the same renderer resolution (38x28), actual Doom geometry
and textures, NTSC TIMEDEMO 3, no explicit VSync, and **Fast DIVU enabled**.
Previous standalone Fast DIVU result: **8.80 average FPS**, 2134 frames,
242.37 seconds at default 68000 clock (BlastEm divider 7). Previous Round 1
baseline without Fast DIVU: **8.70 FPS**. No new FPS numbers are claimed yet.

These changes do **not** change the Black Tiger project, global SGDK install,
or the functional Doom branch. The previous unrolled loops remain disabled.

| ROM name | Flags in addition to Fast DIVU | What it measures |
|---|---|---|
| doom-md-r2-fast-divu.bin | neither | Control for this round |
| doom-md-r2-color-lut.bin | DOOM_CELL_LUT | One 16-bit ROM lookup per textured pixel instead of two chained lookups |
| doom-md-r2-folded-tangent.bin | DOOM_FOLDED_TANGENT | Equivalent quadrant reduction for wall texture angle |
| doom-md-r2-combined.bin | both | Whether benefits add or interact |

### ROM colormap lookup

The build runs `scripts/gen_colormap_cells.py` after `genpal.py`. It reads the
actual big-endian DOOM64KB WAD `COLORMAP` lump and generated `genpal_cell[256]`
mapping. It constructs a **32 x 256 array of final 16-bit VDP tilemap words**,
using exactly the tile attributes as the unchanged C mapping.

The 16,384-byte lookup resides as `static const` in ROM, **not RAM**.
At runtime, the software checks whether a colormap pointer refers to one of
the 32 complete shade rows in `fullcolormap`. If so, the inner textured pixel
loop becomes `screen = cellmap[source[frac >> 9]]`. Otherwise the original
`colorcell[colormap[source[...]]]` remains the fallback. No dynamic palette
invalidation is necessary because gameplay palette flashes update CRAM without
changing the Doom-color-to-VDP-cell indices.

Potential regressions: extra 16KiB ROM, additional per-column selection,
and altered GCC code generation. Validate picture fidelity.

### Folded tangent

The original four branches are replaced by a mirrored 0..2047 lookup index
and a sign. It uses **the same existing tangent table entries** and the
same fixed-point multiplication as the original. The mapping is exhaustively
checked for all 4096 fine angles by
`python3 scripts/bench/test_folded_tangent.py`.

Potential regression: branching and compiler-generated assembly may be less
efficient despite simplifying the source.

## How to run

1. Start the trusted `x360-linux` self-hosted runner as usual.
2. In GitHub Actions select **Renderer optimization - Round 2** and run it on
   `main`. This workflow explicitly checks out `exp/68k-renderer-round2`.
3. Download the **single artifact** `doom-md-renderer-round2-four-roms.zip`.
   It contains four uniquely named `.bin` ROMs, `SHA256SUMS` and `README.txt`.
4. Run each ROM in BlastEm at NTSC, clock divider **7**, normal emulator
   speed. No VSync. Confirm 2134 frames and record average, min, max and time.
5. Compare the reference with the other variants. Check texture shades, doors,
   lifts, and sprites visually. Repeat winning variants **one at a time** to
   exclude multitasking/scheduler effects.

**Do not merge Round 2** until all four ROMs compile, run correctly and the
improvement is reproduced. If the LUT fails the build, read the corresponding
`build-color-lut.log` step output and do not bypass validation.

## Future experiments

If the LUT helps: investigate local lighting table access in masked sprites and
separate output tilemap bandwidth from CPU costs. If tangent folding helps:
consider inspecting GCC-generated 68000 assembly and reducing its multiply
count. Else move to instrumented, finer-grained BSP / `R_StoreWallRange` work.
Do not apply PVS or approximate geometry without separate correctness tests.
