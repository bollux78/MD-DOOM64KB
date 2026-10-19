# R35 SSF2 compatibility probe — EverDrive-MD V2 FW12 / OS36

**This is NOT the Doom playable build.** The ROM checks whether this exact
legacy flashcart supports all three conditions required by a >2 MiB Doom ROM
that depends on SRAM: SSF2 bank switching, ROM above 2 MiB, and SRAM access
without hiding upper ROM.

## Build

Self-hosted GitHub Actions workflow: `.github/workflows/r35-ssf-probe.yml`.
Artifact: `doom-md-r35-ssf-hardware-probe`.
Expected ROM: `doom-md-r35-ssf-probe.bin`, exactly **5,242,880 bytes**
(5 MiB, like Super Street Fighter II). It is generated independently using
SGDK and markers in ROM banks 1, 4, 5, 8 and 9.

Local reproduction, with SGDK/MARSDEV at `~/mars/m68k-elf`:

```fish
fish scripts/lab/build_r35_ssf.fish
```

No WAD, game music, SFX or Doom assets are needed. No firmware or operating
system updates are performed.

## Physical hardware test

1. Copy only the generated .bin file to the microSD, as a regular game.
2. Launch through the old EverDrive-MD OS v36. If its game settings let you
   choose the mapper, select **SSF / SSF2**, not regular MD.
3. Photograph the screen showing all four checks.
4. Report any black screen or freeze, if no screen appears.

The program tests:
- **LINEAR ROM 0-3MiB:** initial direct ROM mapping is as expected.
- **SSF2 BANK 8 / 9:** register `0xA130F3` swaps the 512KiB slot at
  `0x080000` between physical ROM pages 8 and 9.
- **SRAM READ/WRITE:** enable SRAM with `0xA130F1` and round-trip one odd
  byte at `0x200001`, then restore that byte.
- **UPPER ROM WITH SRAM:** a ROM marker at `0x280001` is still visible
  during SRAM access and a marker at `0x200001` returns after disabling SRAM.

Only if ALL checks pass can we safely attempt Doom R31 >2MiB without
SRAM toggling. Passing SSF2 alone is **not** sufficient.

**Caution:** The 2010 EverDrive-MD v2 hardware specification explicitly says
that save RAM is not present in SSF2 mode. We are testing physical compatibility,
not assuming newer Mega EverDrive Pro/X-series hardware features.

**Firmware safety:** Never update the OS or firmware to run this test. Loading
a normal game ROM does not reflash the EverDrive OS.

## Source

- Hardware spec: https://www.scribd.com/document/781754376/everdriveMD-hardware-spec-1-1-Copia
- Legacy EverDrive-MD OS releases: https://stoneagegamer.com/legacy-everdrive-flash-cart-downloads.html
