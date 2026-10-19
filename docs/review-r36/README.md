# R36 Pixel4 Checkerboard Lab — ready for next manual build

**Status:** source implementation prepared; **not compiled or tested on the Mega Drive**. The workflow on this branch is **manual-only**, so commits will not wake or queue a self-hosted runner that is switched off.

## Design

The R35d 8x8 checkerboard remains the graphic reference and is unchanged.
R36 explores *4x4 independent samples* in the original 76x44 Pixel4 renderer:

- Original Pixel4: 16 4bpp color indices, one active 16-color CRAM bank, two 4x4 samples packed per byte.
- R36 Pixel4: 32 **virtual** shades (16 solids plus 16 optimally chosen 50/50 pairs of these CRAM colors). Still one physical 16-color palette during play.
- 1672-byte legacy framebuffer plus **418-byte one-bit plane** for the fifth color-code bit, with the existing bounds guard enclosing both. This is intentionally not an uncompressed 8-bit framebuffer.
- Before compilation, `gen_r36_pixel4_dither.py` reads the same PLAYPAL/R22 palette as the renderer, greedily picks 16 distinct checkerboard blends, and produces two 1024-word Genesis 4bpp row LUTs for even/odd raster rows (**8192 bytes of ROM, no renderer RGB calculations**).
- Each 8x8 VDP tile still has four independent 4x4 picture samples. The pair row LUT alternates pixels on successive raster lines inside each 4x4 sample. Both halves of a VDP tile use the same CRAM bank; *there is no unsupported per-quadrant palette switch*.
- VRAM dynamic banks and solid-tile shortcuts remain at the same positions; mixed tiles are uploaded, solid tiles can still reuse the first 16 immutable tiles.
- No changes to 52 PCM samples, XGM2, gameplay, SRAM bank switching, or full-resolution raw Bayer8 art.
- Screen identity for the Pixel4 variant becomes `R36 P4D - 32 COLORS`.

## Four ROMs after successful manual CI

| Filename | Renderer | Purpose |
| --- | --- | --- |
| `doom-md-r36-cell-play.bin` | 8x8 R35d checker | Playable visual reference |
| `doom-md-r36-cell-perf.bin` | 8x8 R35d checker | DEMO3 FPS reference |
| `doom-md-r36-pixel4-play.bin` | 4x4 R36 32-color dither | Actual Pixel4 visual test |
| `doom-md-r36-pixel4-perf.bin` | 4x4 R36 32-color dither | DEMO3 performance/memory test |

Check the R36 Pixel4 vs. the old R35d `pixel4-*.bin` *not* against the much faster 8x8 renderer. The original Pixel4 pipeline is expensive on the 68000 even without dithering; do **not** infer an FPS gain before testing.

## Tomorrow, with runner on

1. Optional local host-only test: `python3 scripts/lab/test_r36_pixel4_dither.py`.
2. Trigger the workflow `.github/workflows/r35-linear4m.yml` on branch `r36-pixel4-dither` **manually** via GitHub Actions or `gh workflow run r35-linear4m.yml --ref r36-pixel4-dither`.
3. The self-hosted job must build all four ROMs, verify the mapped header/trimmed size, assert flags, count selected checker shades and the RAM/LUT budget, then upload `R36-P4D-FOUR-ROMS.zip`, `R35-AUDIT.json`, `r36-dither-pixel4-{play,perf}.json` and build logs.
4. On real hardware: compare Pixel4 new/old textures, gradients, water, shaded walls, and music/SFX. Run DEMO3 and inspect FPS, minimum free block, and reset stability. Retain R35d 8x8 unless the Pixel4 experiment proves valuable.

### Known risks and audit limits

- No local MARSDEV/68k compiler has been run against this branch. C integration, ROM header and CI packaging remain unverified.
- 418 more bytes of RAM and extra fifth-bit writes/read/dual row-table lookups may reduce Pixel4 FPS. Only a timedemo can establish the actual overhead.
- Checkerboard simulation increases apparent shading but **does not increase the four physical CRAM bank limit** or give the Pixel4 path four simultaneous active palettes.
- Generated values are offline approximations from the baseline PLAYPAL. Color mapping uses the same 16 CRAM entries selected by the original Pixel4 quantizer, then follows Doom palette shift indices. 
