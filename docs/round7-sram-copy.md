# Round 7: SRAM transfer micro-optimizations

Based on `exp/68k-hybrid-cache-round6`, no changes to `main`, R5, or
the working R6 reference.

## Why

R6 Cache16 in 8-bit odd-lane cartridge SRAM completed DEMO3
(2,134 frames) at **8.86 FPS** with 68000 DBRA copies, maintaining
**9,276 B** static work RAM margin, ~2,052 B more than RAM Cache16.
Logical cache stats matched RAM: 15,685 hits, 5,590 misses, 5,574
evictions. The 2-entry RAM hot cache hung; 4-entry hot-cache variants
slowed down. R7 therefore keeps the proven 16-slot SRAM cache without
a RAM front-cache and changes *only* SRAM byte transfer loops.

## Variants

- `asm`: known-good Round 6 assembly DBRA one byte per iteration.
- `unroll4`: four consecutive odd-lane SRAM byte moves per DBRA
  iteration (pointer increments by two for SRAM, by one for RAM).
- `fixed128`: same four-byte unroll, but for 64-byte and 128-byte
  copies uses hard-coded `moveq` group counters. Other lengths use
  the normal unrolled loop.

The renderer passes a 4-byte-aligned column length; for unexpected
unaligned sizes both new variants fall back to R6's scalar DBRA
transfer. Neither touches cache hash/replacement policy. No front
cache; Doom zone remains 43 KiB. Static work RAM is expected to be
the same; verify reports, do not assume it.

## Build (Fish / CachyOS)

```fish
cd ~/Projetos
git clone --branch exp/68k-sram-copy-round7 \
  https://github.com/bollux78/MD-DOOM64KB.git doom-md-r7
cd doom-md-r7
fish scripts/lab/run_round7.fish
```

This writes `dist/doom-md-r7-sram-copy.zip`: three variants × `perf`
and `stats` = six ROMs, compilation logs, static RAM and symbol
reports.

## Test protocol

BlastEm 1.0.0 only, NTSC 60 Hz, standard 68000 divider 7:
run the three `perf` ROMs and record average FPS, min/max 15-second
FPS, 2,134 frames, seconds. Run `stats` ROMs after and check they all
match **15,685 / 5,590 / 5,574** hits/misses/evictions.

Baseline: R6 SRAM ASM **8.86 FPS**; RAM16 **9.06 FPS** (no SRAM).
Do not infer success from compilation alone: assembler syntax and
runtime behavior have not been independently verified for new paths.

**Hardware safety:** All SRAM variants write to the cartridge save
RAM space at `0x200001` onward. Do **not** test them on Mega Drive
hardware with a cartridge/flashcart until its exact SRAM mapping and
save protection behavior are verified; existing save data can be
overwritten. RAM-only ROMs are not subject to this SRAM write risk.
