# R6 stable continuation — reset after R7

R7 PR #9 was closed **without merge** following reproducible black-screen
failures in its ASM / Fixed128 performance ROMs and Unroll4 stats ROM.
The R6 source remains unchanged; this branch originates directly from
`exp/68k-hybrid-cache-round6` and deliberately contains **no R7 code**.

## Validated reference (BlastEm 1.0.0)

- Cache16 SRAM ASM: **8.86 FPS**, 2,134 DEMO3 frames, 240.73 seconds
- 15,685 cache hits / 5,590 misses / 5,574 evictions
- Static RAM free: 9,276 bytes (2,052 bytes more than RAM16)
- Original 68000 clock, NTSC 60 Hz, 43 KiB Doom zone

First rebuild the **exact R6 ASM configuration**, without front-cache and
without any R7 transfer macros:

```fish
cd ~/Projetos
git clone --branch exp/68k-sram-r6-stable-next \
    https://github.com/bollux78/MD-DOOM64KB.git doom-md-r6-next
cd doom-md-r6-next
fish scripts/lab/run_r6_stable_control.fish
```

Expected output: `dist/doom-md-r6-stable-control.zip`, including two
ROMs, one `perf`, one `stats`, plus linker RAM and build reports.

**Stop criterion:** if either ROM fails to complete the demo or if stats
differ, do not introduce any optimization. A rebuild can alter binary
layout, so establishing a fresh reproducible reference is mandatory.

After the baseline is validated, future optimizations must be introduced
in a separate child branch and benchmarked one at a time, each with
`perf` + `stats` and unchanged Doom heap.

**Hardware caution:** this experiment writes to odd-byte-lane cartridge
SRAM. Use BlastEm for these variants, not physical Mega Drive cartridges
or flashcarts unless SRAM mapping and save preservation are explicitly
verified.
