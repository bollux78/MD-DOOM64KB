# DOOM MD — Round 5: RAM budget and zone experiments

## Why

BlastEm 1.0.0 results: Cache8/16 complete DEMO3; Cache32 can hang;
Cache64 throws a 68000 Address Error. Static R4 reports show:

| Cache | .data+.bss | Remaining below stack top |
|---|---:|---:|
| 8  | 57,272 B | 8,264 B |
| 16 | 58,312 B | 7,224 B |
| 32 | 60,392 B | 5,144 B |
| 64 | 64,552 B |   984 B |

**New code finding:** `src/i_genesis.c` reserves an additional *fixed*
43 KiB Doom zone array (which is already INCLUDED in .data+.bss above).
Reducing that zone is a trade-off, **not** automatic safe RAM recovery.

## Variants

Run `fish scripts/lab/run_round5.fish` on the R5 branch in the existing
CachyOS development checkout (no new SDK required).

The matrix is:

- cache16 / zone43 (control), cache16 / zone39 (zone pressure control)
- cache32 / zone43, zone41, zone39 (diagnose whether more stack margin helps)
- cache64 / zone39 (compile for inspection; unsafe to execute until reviewed)

For each pair: one `-perf` ROM (no diagnostic counters) and one `-ram`
ROM (zone accounting + sampled stack SP, may lower FPS). This creates twelve
ROMs, two static reports per ROM, build logs and a ZIP in `dist/`.

## What the diagnostic screen means

- **ZONE CAPACITY**: fixed zone size available to Doom, after its alignment.
- **ZONE PEAK USED**: highest sum of live allocated zone blocks, including
  allocator headers and internal fragmentation.
- **ZONE LIVE NOW**: allocated zone bytes at the end of DEMO3.
- **ZONE FREE NOW**: sum of free blocks when DEMO3 ends; this is *not*
  the largest allocatable contiguous block.
- **PEAK ZONE LEFT**: capacity minus observed peak live bytes, which is *not*
  necessarily the maximum safe further allocation due to fragmentation.
- **STACK GAP SAMPLED**: minimum sampled A7 minus ELF `_bend`. Sampling
  happens in BSP subsector traversal and once per benchmark frame.
  It **does not** include all ISR/call-chain depths and is not a stack
  high-water mark. Positive samples do not prove stack safety.

The `symbols-*.txt` reports rank largest RAM symbols using
`m68k-elf-nm -a -S`; they do not count all linker alignment/padding.
The `ram-*.txt` reports remain the source of truth for static headroom.

## Testing protocol

Use **BlastEm 1.0.0**, NTSC 60 Hz, original 68000 divider 7.
Fast-forward may accelerate wall-clock execution; FPS reported by the ROM
is still based on emulated VBlank time. Compare FPS from `-perf` only.

1. Run cache16-zone43-ram and verify DEMO3 finishes and metrics appear.
2. Run cache16-zone39-ram; check for out-of-zone allocation failures.
3. Run cache32-zone39-ram *only in the emulator*; if it hangs, terminate it.
   Record if/how far it progressed and any error address.
4. Try cache32-zone41-ram if 39 is stable or to bracket the limit.
5. Keep cache64 untested until sufficient heap and stack margin are proven.

A ROM passes only if **all 2,134 frames complete** and no address error
or memory allocator failure occurs. Compare completed `-perf` variants
against R4 cache16, 9.06 FPS on BlastEm 1.0.0. Do not merge unverified
changes into the stable branch, and **never run Cache32/64 on hardware**.

## Limitations and next step

This R5 establishes whether reducing the fixed Doom zone can free enough
RAM for larger composed-column caches **without starving the actual game**.
If zone usage is close to 39 KiB, reverting to 43 KiB and targeting other
buffers is preferable. A future full stack canary/high-water implementation
would require accounting for SGDK-owned memory and interrupts; R5 does not
pretend that a sampled stack address provides this guarantee.

The workflow `.github/workflows/memory-optimization-round5.yml` is manual
and self-hosted. GitHub usually requires `workflow_dispatch` workflows to
exist on the default branch before they appear in Actions. Until the R5
workflow is reviewed and merged, use the fish script locally; no runner
changes are required.
