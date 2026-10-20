# DOOM-MD R46 M3C R2 — VRAM guard investigation, six-ROM A/B

## Why R2 exists

User observation on M3C: one graphics lockup in five runs of the
`m3c-video-perf` diagnostic; other builds completed DEMO3. The M3C
diagnostic is NOT approved for hardware. A BlastEm 480-frame smoke
test returning process status zero is not a visual or long-run stability
test. The cause has not been isolated.

Reported benchmark context: Primary 11.77 FPS / 181.25 s, M2C
11.76 / 181.50 s, M3B 11.76 / 181.50 s, and M3C 11.77 / 181.35 s,
all 2134 frames. These rates establish *no measurable rendering-speed
benefit*, as Doom still draws with the 8×8 pipeline after the diagnostic.

## Concrete VRAM collision audit (64×32 H40, SGDK)

| VRAM addresses | Owner / risk |
|:--|:--|
| 0x06C0–0x6A7F | pixel4 dynamic bank0 |
| 0x6F40–0xD2FF | pixel4 dynamic bank1 |
| 0xC000–0xCFFF | BG_B 64×32 name table — overwritten by bank1 |
| 0xD000–0xDFFF | Window H40 64×32 name table — first 0x300 bytes overwritten |
| 0xD400–0xDFFF | SGDK font — must NEVER be blanket-cleared |
| 0xE000–0xEFFF | BG_A 64×32 safe name table |
| 0xF000–0xF3FF | horizontal scroll table (not touched) |
| 0xF400–0xF7FF | sprite attribute table (not touched) |

R2 corrects a SECOND previously unprotected overlap: the Window
tilemap begins at D000. Both BG_B and Window are temporarily mirrored
to the existing safe BG_A map at E000 while diagnostic bank1 is active.
Restoration returns BG_B to C000 and Window to D000. It explicitly
clears only Window rows 0..5, 64 entries each, corresponding to
D000..D2FF; all font pixels D400..DFFF are left intact.

R2's M3C palette restoration is synchronous via CPU writes, rather
than queuing a 64-color DMA update that could execute after ownership
returns to 8×8. The pre-existing M3B is unchanged. The 8×8 tile
patterns, BG_A/B map state and shared frame buffer are restored before
DEMO3. The M3A barrier still represents caller acknowledgments, not
automatic hardware verification.

## Six comparative ROMs

1. `doom-md-r46-primary-perf.bin` — 8×8 control
2. `doom-md-r46-m2c-perf.bin` — dual-linked helpers, 8×8 active
3. `doom-md-r46-m2c-play.bin` — gameplay/audio
4. `doom-md-r46-m3b-video-perf.bin` — approved single-bank baseline
5. `doom-md-r46-m3c-r2-safe-perf.bin` — M3C with CPU tile patterns
   uploaded while the display is disabled. Four pattern phases. This
   favors safety over uninterrupted animation and may blank longer.
6. `doom-md-r46-m3c-r2-stress-perf.bin` — M3C with hidden-bank
   patterns uploaded while the prior bank remains visible; 12
   phases (three loops of four) amplify intermittent contention.

Only the last two ROMs use the changed M3C diagnostic. Do not confuse
`doom-md-r46-m3b-video-perf` with the dual-bank tests.

## Tests and acceptance

- Native oracles: 4×798 tile words and bank state machine, plus the
  R2 Window/Font VRAM boundary and source audit, after all earlier
  M2C/P2A–P2I and M3A/M3B tests.
- Five or more BlastEm boot runs per variant are useful; single
  300/550/1150-frame smokes do not establish full stability.
- CI compiles six ROMs and verifies flags, linked functions, RAM,
  ROM header, and basic BlastEm startup.
- User: test **safe** five runs and **stress** five runs separately,
  noting in which phase corruption or lockup occurs. Also check
  restoration to DEMO3 and repeat at least once with sound enabled.
- Hardware: do NOT deploy R2 on Mega Drive until safe and stress
  comparison is understood. The approved M3B remains the video baseline.

## Explicit limits

Neither variant is a playable 4×4 Doom nor a seamless bank flip. A
full upload is 798×32=25,536 bytes, followed by at least
21×38×2=1,596 map bytes. The current diagnostic uses CPU VRAM
uploads and temporarily blanks the display while the single safe
tilemap is rebuilt. This is not a 60 Hz frame-delivery design.

Next decisions depend on the actual comparative error rate:
- Failures limited to stress suggest active-display write contention
  or timing during long VRAM pattern uploads.
- Both failing suggest persistent Window/BG_B/SGDK state, init/restore
  race, stack, audio VBlank callback or another unknown root cause.
- Neither failing in 5 runs is encouraging, not proof of zero errors.
