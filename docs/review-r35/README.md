# R35 — Mega Drive linear ROM up to 4 MiB; no runtime asset compression

Base: `r31-sfx-pcm` (R31 mixed genuine PCM, full XGM2 episode soundtrack).
This branch is deliberately **NOT SSF2**; it maps 0x000000-0x3FFFFF
directly, and it keeps the R31 SRAM switching at 0xA130F1. Target:
legacy EverDrive-MD clone, OS v36 / FW12.

## Four ROMs in one ZIP
`R35-FOUR-ROMS.zip` (inside the GitHub Actions artifact
`doom-md-r35-linear4m-raw-bayer8`).

- `doom-md-r35-cell-play.bin` — playable, R31 8x8 solid-color 3D renderer.
- `doom-md-r35-cell-perf.bin` — same renderer, timedemo DEMO3.
- `doom-md-r35-pixel4-play.bin` — playable, R22 independent 76x44
  4x4 sample renderer with SOLID_TILES + PAIR_LUT.
- `doom-md-r35-pixel4-perf.bin` — same 4x4 renderer, timedemo DEMO3.

All ROMs are **exactly 4,194,304 bytes** (0x400000, 4MiB). Actual
linked code/data footprint is reported independently; the unused end
of each image is padded 0xFF. R35 build fails if it exceeds 4MiB.
A correct SEGA MEGA DRIVE header declares ROM end 0x003FFFFF.
No SSF bank switching, no extra ROM mapping register writes.

## Uncompressed assets / invariant

- Genuine Doom **52 PCM effects**, using exactly the R31 `mixed`
  generator and XGM2 playback, without R34 ADPCM/RLE.
- Optimized E1M1..E1M9 and other screen **XGM2 tracks untouched**.
  All four variants use the same R31 playlist and music preparation.
- Repacked aligned R24 episode WAD, with unchanged R31 deduplication.
  Dedup means shared identical lumps reference a single uncompressed
  payload; there is no runtime codec. No R34 REJECT compression.
- R30 320x224 native title/intermission/finale at 4bpp with the
  existing adaptive **Bayer8** quantization; every unique tile is stored
  as **32 raw bytes** rather than byte RLE. Identity and size audited.
- In 4x4 gameplay builds, static screens temporarily use the same
  native 320x224 Bayer8 artwork. The renderer restores its solid VRAM
  tiles on return to gameplay. **This transition is experimental and
  must be verified in BlastEm and on hardware.**
- 4x4 gameplay uses 76x44 independent color samples, not 8x8 tiles
  simply enlarged. It has a different pixel palette and VDP upload
  cost from the 8x8 version.

## Reproducible local build (fish)

```fish
fish scripts/lab/build_r35_linear.fish
```

Requires installed `~/mars/m68k-elf`, original `doom1.wad` source
available to the R31 SFX generator, and the pinned WAD/art/music inputs
already provided by the R31 build environment. On GitHub, the
`.github/workflows/r35-linear4m.yml` CI provides the same preflight
as R31, builds all four ROMs, audits the header/size/source art and
uploads a single ZIP.

## Hardware test order

1. First run `cell-play`. It should behave like R31 except the
   raw art image and 4MiB linear ROM layout.
2. Then `pixel4-play`. Check title art, first level, HUD, SFX, music,
   intermission and return to gameplay. This mode may regress.
3. Run each `*-perf` at the same **7.67 MHz 68000** as previous
   DEMO3 comparisons; photograph average/min/max FPS.
4. Reject changes that show bad graphics, black screen, SRAM errors,
   or recurring crashes even if FPS increases.

No performance or physical-cart compatibility claim is made until
play and perf are tested; CI only verifies compilation and asset format.
