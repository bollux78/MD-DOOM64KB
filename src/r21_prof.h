/* R21 N7b: statistical PC profiler on the horizontal interrupt (diagnostic).
 * Histogram lives in cartridge SRAM (odd bytes, 0x200001..0x20FFFF), so it
 * costs no work RAM and survives in BlastEm's .sram file / a flash cart.
 * Read it with scripts/lab/r21_profile.py. GPL-2.0-or-later. */
#ifndef R21_PROF_H
#define R21_PROF_H
#include <stdint.h>
#if defined(DOOM_R21_PROF)
#define R21_PROF_BASE     0x00000200u   /* first code byte after the header */
#define R21_PROF_SHIFT    5             /* 32-byte buckets */
#define R21_PROF_BUCKETS  16368u        /* 32 header bytes + 2*16368 = 32 KB */
#define R21_PROF_LINES    16            /* one sample every 16 active lines (~840 Hz) */
extern volatile uint32_t r21_prof_samples, r21_prof_bad, r21_prof_out;
extern uint8_t r21_prof_state;          /* 0 off, 1 armed, 2 ROM>2MB, 3 done */
void R21_ProfInit(void);                /* boot: SRAM on, clear histogram */
void R21_ProfStart(void);               /* DEMO3 start */
void R21_ProfStop(uint32_t frames);     /* before the result screen */
#endif
#endif
