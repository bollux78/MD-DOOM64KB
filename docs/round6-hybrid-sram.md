# R6 — Hybrid Cache16 and 68000 SRAM copies

Branch: `exp/68k-hybrid-cache-round6` (based on `exp/68k-sram-cache16`).
The finished R5 and original RAM Cache16 are unchanged.

The previous BlastEm 1.0.0 DEMO3 baseline (no overclock):
- RAM Cache16: **9.06 FPS**, **7224 bytes** static RAM margin.
- SRAM Cache16 (8-bit odd cartridge SRAM): **8.73 FPS**, **9276 bytes** static RAM margin.
- Both achieved 15,685 hits / 5,590 misses / 5,574 evictions in stats ROMs.

## R6 variants

| Prefix | Location / changes | Expected trade-off |
|---|---|---|
| ram16 | RAM Cache16, control | 9.06 FPS reference |
| sram16 | SRAM Cache16, C copies | 8.73 FPS reference |
| sramasm | SRAM Cache16, DBRA assembly transfer | Test transfer loop |
| hot2 | SRAM 16 entries + 2×128 byte RAM front cache | More RAM, potentially fewer SRAM reads |
| hot4 | SRAM 16 entries + 4×128 byte RAM front cache | More RAM, potentially fewer SRAM reads |
| hot4asm | hot4 + DBRA assembly transfers | Combined experiment |

The RAM front-cache keeps tags including the original logical SRAM slot and texture key.
This preserves the existing 16-slot hash, replacement, and hit/miss counters.
On SRAM cache hits, it returns a recent RAM buffer if found, otherwise loads
the SRAM column. SRAM remains authoritative for all 16 slots; on a miss, a
new column is composed into the existing 128-byte staging buffer and saved to
SRAM, then copied into the RAM front-cache. Neither hot-cache size is guaranteed
to be faster because copies, comparisons, and LRU updates also consume time.

The 68000 assembly variant uses byte moves and DBRA, handling SRAM's **odd-byte
data lane** (the Mega Drive SRAM address increments by 2). This is not a
DMA transfer, not word-wide SRAM, and not a clock speedup.

## Local build

Use a clean, separate checkout:

```fish
cd ~/Projetos
git clone --branch exp/68k-hybrid-cache-round6 \
    https://github.com/bollux78/MD-DOOM64KB.git doom-md-r6
cd doom-md-r6
fish scripts/lab/run_round6.fish
```

Creates `dist/doom-md-r6-hybrid-sram.zip`, 12 ROMs (six variants,
`perf` and `stats`), compiler logs, static RAM reports and symbol reports.

## Measurement

BlastEm **1.0.0**, NTSC 60 Hz, original 68000 divider 7, timedemo DEMO3
with 2,134 frames, wait-free rendering. Run `perf` builds for FPS and the
`stats` builds for logical-cache counter equivalence. All variants use 43 KiB
zone; none relies on the R5 reduced-heap experiment.

Test order: ram16-perf, sram16-perf, sramasm-perf, hot2-perf,
hot4-perf, hot4asm-perf. If one hangs, stop it and record the variant;
do not interpret a hang as low FPS. Stats should preserve 15685 hits,
5590 misses, 5574 evictions for the DEMO3; front-cache hits are not
separately counted. The CPU assembly routines need cross-compilation and
emulator execution to validate their register constraints and behavior.

**Emulator-only:** these ROMs write to mapped cartridge SRAM during
initialization and runtime. Do not try them on a physical cartridge or flashcart,
especially one with save data.

Experiment not yet cross-compiled or measured by assistant; only source
implementation is committed. No automatic merge into main.
