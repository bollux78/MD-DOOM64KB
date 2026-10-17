/* R21 N7b: statistical PC profiler (diagnostic only). See r21_prof.h.
 * GPL-2.0-or-later. */
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "r21_prof.h"
#if defined(DOOM_R21_PROF)
#if !defined(HINTERRUPT_CALLBACK)
#error R21 profiler needs SGDK >= 1.80 (HInt vector jumps straight to the callback)
#endif
#define SRAMB(k) (*(volatile uint8_t *)(0x200001u + 2u * (uint32_t)(k)))
extern void R21_ProfHInt(void);
volatile uint32_t r21_prof_samples, r21_prof_bad, r21_prof_out;
uint8_t r21_prof_state;

static void put32(uint16_t k, uint32_t v)
{
    SRAMB(k) = (uint8_t)(v >> 24); SRAMB(k + 1) = (uint8_t)(v >> 16);
    SRAMB(k + 2) = (uint8_t)(v >> 8); SRAMB(k + 3) = (uint8_t)v;
}

void R21_ProfInit(void)
{
    /* With a ROM above 2 MB the SRAM window would hide ROM: refuse. */
    uint32_t rom_end;
    __asm__ volatile ("move.l 0x1A4,%0" : "=d" (rom_end));   /* header: ROM end */
    if (rom_end > 0x1FFFFFu)
    {
        r21_prof_state = 2;
        return;
    }
    *(volatile uint8_t *)0xA130F1 = 1;     /* SRAM_enable(): read/write */
    for (uint16_t k = 0; k < 32768u; k++)
        SRAMB(k) = 0;
    SRAMB(0) = 'R'; SRAMB(1) = '2'; SRAMB(2) = '1'; SRAMB(3) = 'P';
    SRAMB(4) = 1;                          /* layout version */
    SRAMB(5) = R21_PROF_SHIFT;
    put32(6, R21_PROF_BASE);
    SRAMB(10) = (uint8_t)(R21_PROF_BUCKETS >> 8);
    SRAMB(11) = (uint8_t)R21_PROF_BUCKETS;
    SRAMB(28) = R21_PROF_LINES;
    r21_prof_state = 1;
}

void R21_ProfStart(void)
{
    if (r21_prof_state != 1) return;
    r21_prof_samples = r21_prof_bad = r21_prof_out = 0;
    SYS_setHIntCallback(R21_ProfHInt);
    VDP_setHIntCounter(R21_PROF_LINES - 1);
    VDP_setHInterrupt(TRUE);
}

void R21_ProfStop(uint32_t frames)
{
    if (r21_prof_state != 1) return;
    VDP_setHInterrupt(FALSE);
    SYS_setHIntCallback(NULL);
    put32(12, r21_prof_samples);
    put32(16, r21_prof_bad);
    put32(20, r21_prof_out);
    put32(24, frames);
    r21_prof_state = 3;
}
#endif
