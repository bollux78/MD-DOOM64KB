# R46 M3C R4 — Stabilize SGDK heap without sacrificing corrected font

## New finding from R3 screenshot

The R3 SAFE and STRESS result screens are visually correct and report
11.80 FPS / 180.92 s on 2134 frames, nearly the Primary 11.80 / 180.82.
R2 SAFE and STRESS still exhibit colorful font corruption.

However, R3 ends with R28 `ERRORS=2` and `RAW FREE=3514`, compared
to Primary `ERRORS=0`, `RAW FREE=1386` (and M3B errors=0, free=1382).
In `src/i_genesisv.c`, bit 2 indicates that the original 2128-byte
video snapshot buffer no longer has its expected SGDK heap-block header
`2128+3=2131`. The difference of about 2130 bytes in free space raises
a serious question about a stale, freed or reused heap allocation.
A visually correct font alone is NOT sufficient for R4 approval.

## Probable trigger

SGDK `updateMapsAddress(FALSE)`, invoked by `VDP_setBGBAddress`
and `VDP_setWindowAddress`, changes `maps_addr`, implicitly calls
`VDP_loadDefaultFont(CPU)` (which unpacks the font through the SGDK
allocator), then calls `MEM_pack()`. During M3C R2/R3 we invoked
these setters repeatedly while the DOOM R20 video-copy buffer was
allocated. This explains font movement and warrants investigating the
heap header mismatch, but the **specific memory failure is not proven**.

## Controlled R4 experiment

Physical H40 VDP registers permit a temporary plane mirror WITHOUT
calling the SGDK setters or changing SGDK's cached map base:

- Reg 4 = `0x8407` redirects BG_B to E000.
- Reg 3 = `0x8338` redirects WINDOW to E000.
- Reg 3 = `0x8334` restores WINDOW to D000.
- Reg 4 = `0x8406` restores BG_B to C000.

R4 uses these raw control port writes only during an EXCLUSIVE,
display-disabled diagnostic. All normal SGDK cached map addresses
remain original (BG_B C000, WINDOW D000, BG_A E000, maps_addr C000).
The original 96-font atlas B400..BFFF is still overwritten by bank1,
so R4 retains R3's explicit, synchronous post-handoff
`VDP_loadDefaultFont(CPU)` with status check and DMA drain.

No SGDK BG_B or Window access is allowed until their physical
registers are restored. Outside this diagnostic, the SGDK state is
identical to the original. This deliberately avoids interim font
decompression and heap repacking triggered by map setters. It does NOT
eliminate all SGDK heap activity because the final explicit reload
still temporarily decompresses the font.

## Eight builds in the comparison

1. `doom-md-r46-primary-perf.bin` — approved 8×8 baseline
2. `doom-md-r46-m2c-perf.bin` — helpers co-linked
3. `doom-md-r46-m2c-play.bin` — original PLAY
4. `doom-md-r46-m3b-video-perf.bin` — stable single bank
5. `doom-md-r46-m3c-r3-safe-perf.bin` — visually fixed, ERRORS=2
6. `doom-md-r46-m3c-r3-stress-perf.bin` — visually fixed, ERRORS=2
7. `doom-md-r46-m3c-r4-safe-perf.bin` — raw reg mirror, 4 phases
8. `doom-md-r46-m3c-r4-stress-perf.bin` — raw reg mirror, 12 phases

CI verifies all compiled ROMs, BSS deltas, unmodified baseline,
explicit compiler flags, existing P4 oracle and new raw register
source contract. BlastEm boot smoke does not prove that the R28
heap error is gone. In screenshot validation, **require** BOTH:
legible glyphs in R4 results and `RAW FREE / ERRORS` matching
the baselines (particularly ERRORS=0, expected ~1384 free).
If the error persists despite raw plane registers, next isolate
the final explicit font decompress/SGDK MEM allocator; do not hide or
disable the audit.

Do not run the diagnostic on a physical Mega Drive until it passes
these two checks consistently in BlastEm.
