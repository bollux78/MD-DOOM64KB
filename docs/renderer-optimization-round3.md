# DOOM MD — Round 3 optimization laboratory

The starting point is **Fast DIVU + Color LUT**, which measured 8.91 FPS
in Round 2 (2134 frames, 239.48 seconds, NTSC, 68000 divider 7, NO VSync).
The combined Color LUT + Folded Tangent version measured 8.92 FPS, a
difference too small to justify extra complexity without isolated re-tests.

Round 3 deliberately retains **Color LUT and Fast DIVU** and disables
Folded Tangent and unrolled columns. There are no changes to geometry,
texture quality, screen resolution or the SGDK toolchain.

## Individual experiments

| Artifact ROM | Change | Purpose |
|---|---|---|
| `doom-md-r3-baseline.bin` | none beyond Fast DIVU + Color LUT | Confirm local current baseline |
| `doom-md-r3-masked-divu.bin` | `DOOM_MASKED_DIVU=1` | Use the same bit-exact 68000 DIVU.W shortcut when drawing masked wall textures |
| `doom-md-r3-cache8.bin` | `DOOM_CACHE8=1` | Double the cache for composite texture columns from four to eight entries (+512 bytes of RAM) |
| `doom-md-r3-combined.bin` | both flags | Measure interaction |

The masked reciprocal preserves
`(0xffffffffu / scale) >> 7 == 0x01ffffffu / scale`
for nonzero unsigned scale. The fast DIVU.W path is only used for scales
in the safe interval 512..65535, with the unchanged original expression
outside this interval. The source already contains this exact approach
for ordinary wall columns.

For cache8, the original hashing and replacement algorithm is maintained,
except it now has eight slots. The number of collision probes remains four
so a larger cache cannot itself add a longer probe loop. Larger cache may
reduce repeated texture assembly, or may not help at all.

## How to test

1. First repeat the previous `doom-md-r2-color-lut.bin` and
   `doom-md-r2-combined.bin` **one emulator at a time**. Confirm that
   screenshots are visually identical to the corresponding control.
2. Start the trusted local `x360-linux` runner and manually run
   [Renderer optimization - Round 3](https://github.com/bollux78/MD-DOOM64KB/actions/workflows/renderer-optimization-round3.yml)
   from the **main** branch. The job checks out
   `exp/68k-renderer-round3` and builds all four ROMs serially.
3. Download `doom-md-renderer-round3-four-roms.zip` (one artifact).
   It contains four separately named ROM files and SHA256SUMS.
4. Test each ROM in BlastEm (NTSC, divider 7, normal speed,
   no emulated CPU overclock, DEMO3 2134 frames), and record FPS mean/min/max
   and duration. Compare **relative to the Round 3 baseline generated in
   the same run**, then repeat the winning variant isolated.
5. If a visual mismatch appears in masked transparent textures, do
   **not** merge. If cache8 does not provide measurable performance benefits,
   restore four entries to save 512 console RAM bytes.

No automated emulator benchmark or automated visual QA is claimed; Github
Actions compiles the four binaries and checks the reciprocal identity,
but measurements still require the emulator.

## Next direction

Split the broad `BSP TRAVERSE` profiler stage into `R_CheckBBox`,
`R_AddLine`, `R_StoreWallRange` and true BSP descent before
optimizing that code. Investigate cache hit/miss instrumentation rather than
assuming cache8 is beneficial.

**Do not merge the draft PR until ROMs compile and are validated.**
