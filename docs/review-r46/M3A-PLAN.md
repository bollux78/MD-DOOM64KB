# DOOM-MD R46 M3A — safe handoff preconditions + generic pixel4 tile packing

Base: **P2I approved by user**, all 3 ROMs functional; R39f control
11.80 FPS / 180.82 s, M2C 11.78 FPS / 181.12 s, 2134 DEMO3 frames,
no errors. No new gameplay-resolution switch is permitted in M3A.

## Batch changes

### M3A-A — explicit framebuffer/VDP ownership state machine

`r46_m3_owner.{h,c}` introduces a caller-owned renderer-mode record with
states ACTIVE, QUIESCE and RECONFIGURE. A request to change renderer
ownership invalidates both writers until the caller acknowledges that:

1. Pending old DMA has REALLY finished.
2. ISR/VBlank access to the old framebuffer has REALLY been disabled.
3. Target VRAM pattern bank, CRAM and tilemap have REALLY been rebuilt.

A commit makes the new owner active only after all five acknowledgments.
`R46_M3_MayWrite()` rejects access while reconfiguration is incomplete.
A transition may be aborted only in QUIESCE, before VDP reconfiguration.

**Critical:** these functions encode *preconditions*, but do NOT stop DMA,
mask interrupts, wait for VDP, touch `_s_screen`, upload tiles, change CRAM
or make switching safe by themselves. Acknowledgment bits are caller
assertions, not automated hardware verification. The VDP-facing owner
implementation and real IRQ synchronization must be built/tested in M3B.

### M3A-B — source-independent tile row and 32-byte pattern encoder

`r46_m3_tiles.{h,c}` takes any caller-owned packed 1672-byte 76×44
frame and emits tile map entries or 8×32-bit pattern rows using the
exact R46 M1B/R22 two-bank mapping. No global shared framebuffer pointer
is accessed. `R46_M3_PackOwned` requires a fully committed pixel4 owner;
invalid/solid tile calls leave output untouched. Preserve text sample rows
0..1. Dynamic tiles in bank0 occupy 54..851 and in bank1 890..1687,
below font tile 1696.

A host C oracle tests 28 frame patterns across both banks (44,688
tile checks), comparing every index and 32-byte dynamic tile against
the existing proven M1B implementation. Tests also cover all ownership
transitions and no-write behavior before commit. If every tile is
dynamic the transfer would be 798×32 = **25,536 VRAM pattern bytes per
complete 38×21 map bank**, excluding map and DMA bookkeeping; actual
speed and DMA scheduling remain to be benchmarked in a later build.

## CI and acceptance

- Run prior P2A–P2I oracles and new M3A host oracle.
- Build primary PERF, experimental M2C PERF, M2C PLAY.
- Verify linked M3A entry points only in experimental variant.
- Preserve primary R39f tile renderer and SGDK free RAM; no added .bss.
- ROM integrity and BlastEm 300-frame smoke for each variant.
- Manual complete DEMO3 vs control and PLAY verification.

## Next gates

M3B: actual *exclusive* frame owner and VDP upload/IRQ drain, with
isolated visual test ROM(s) for the 4×4 path and rollback; do not switch
resolution in production until verified. M4: connect native Doom camera/BSP,
flats/texture columns, sky/HUD/weapon, and user-facing resolution dispatcher.
The host packet encoder alone does not represent playable 4×4.
