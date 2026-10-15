# Round 5 follow-up — Cache16 in cartridge SRAM

**Experimental branch:** `exp/68k-sram-cache16`, based on
`exp/68k-memory-round5`. This does not change `main` or the R5 branch.

## Hardware mapping and correctness

The existing ROM header already advertises battery-backed SRAM
(`RA`, flags `F820`, range `0x200000..0x20FFFF`).
The ROM image is approximately 1.5 MiB, below the SRAM window at 2 MiB.

Conventional Genesis cartridge SRAM is **8-bit, odd-byte lane only**:
`0x200001`, `0x200003`, ..., `0x200FFF` store the 2,048 bytes for
the 16 cache slots. These are *not* contiguous 68000 bytes. The
renderer **must not** use an SRAM pointer as `dcvars->source`, nor
copy with `_fmemcpy` directly to this SRAM mapping.

Instead the test uses the already-existing 128-byte `tmpCache` RAM
buffer as a staging column:
- On a cache miss, compose into `tmpCache`, then write the valid bytes
  into odd-lane SRAM addresses.
- On a cache hit, copy the column back from SRAM into `tmpCache`.
- Draw from the same `tmpCache` pointer in both cases.
- Cache tags, probing, slot count, Doom zone (43 KiB), render settings,
  and timedemo remain unchanged.

Expected static RAM saving: about **2,048 bytes**, minus any extra
compiler-generated static bookkeeping (normally negligible). Extra
SRAM transfers can reduce FPS significantly; this is a measurement,
not a claimed optimization.

At startup, the ROM enables cartridge SRAM using the control register
`0xA130F1` and checks that first and last test bytes are writable
and independent. It restores their original values. If the test fails,
the ROM displays **SRAM CACHE16: SRAM NOT FOUND** and does not run
the benchmark. A successful startup check is not proof of long-term
reliability.

## Build and test

Create a **separate checkout** from the user's modified Doom worktree:

```fish
cd ~/Projetos
git clone --branch exp/68k-sram-cache16 \
    https://github.com/bollux78/MD-DOOM64KB.git doom-md-sram
cd doom-md-sram
fish scripts/lab/run_sram_cache16.fish
```

The script creates `dist/doom-md-r5-sram-cache16.zip` with four ROMs:

| ROM | Storage | Instrumentation |
|---|---|---|
| `doom-md-r5-ram16-perf.bin` | Main RAM | None |
| `doom-md-r5-sram16-perf.bin` | Cartridge SRAM | None |
| `doom-md-r5-ram16-stats.bin` | Main RAM | Cache hits/misses |
| `doom-md-r5-sram16-stats.bin` | Cartridge SRAM | Cache hits/misses |

For apples-to-apples comparison, use **BlastEm 1.0.0**, NTSC 60 Hz,
original 68000 clock divider 7, DEMO3 (2,134 frames), and compare
the two `perf` ROMs only after full completion. Use the two
`stats` ROMs to verify hit/miss counts remain consistent; they
have instrumentation overhead and are not valid for ranking FPS.
Compare `ram-*.txt` and `symbols-*.txt` to quantify actual static
RAM recovered.

**Emulator-only experiment. Do not run on physical hardware or a
flashcart**: many flashcarts use different SRAM mappings or have
battery-backed user data, and the test writes to SRAM.

## Interpretation

If SRAM ROM fails at startup, confirm that BlastEm supports the
header-advertised cartridge SRAM and has SRAM enabled for this ROM.
If it completes but FPS falls, the transfer overhead exceeds the
benefit of freeing work RAM; a future variant could use SRAM only for
cold data or a small RAM front-cache. Do not conclude SRAM is faster
merely because static RAM headroom increased.
