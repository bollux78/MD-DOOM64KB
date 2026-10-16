/* R19 diagnostic: bounded zone walk and approximate 68000 stack high-water.
 * No SRAM and no modifications to Doom's allocator behavior.
 * The watermark covers only currently UNUSED RAM between _bend and the
 * stack at I_InitGraphics. Stack used before initialization is not measured.
 */
#include <stddef.h>
#include <stdint.h>
#include "compiler.h"
#include "r19_memdiag.h"
#include "z_zone.h"

#if defined(DOOM_MEM_DIAG)
extern uint8_t _bend; /* SGDK md.ld: first byte after static .data/.bss */
r19_memdiag_t r19_memdiag;
static volatile uint8_t *watermark_begin;
static volatile uint8_t *watermark_end;
static uint16_t frame_counter;

static uintptr_t r19_read_sp(void)
{
    uint8_t *sp;
    __asm__ volatile ("move.l %%sp,%0" : "=a" (sp));
    return (uintptr_t)sp;
}

static uint16_t r19_gap(uintptr_t sp)
{
    uintptr_t bend = (uintptr_t)&_bend;
    if (sp <= bend) return 0;
    uintptr_t gap = sp - bend;
    return (uint16_t)(gap > 65535u ? 65535u : gap);
}

void I_MemDiagInit(void)
{
    uintptr_t bend = (uintptr_t)&_bend;
    uintptr_t sp = r19_read_sp();
    r19_memdiag.zone_free = 0;
    r19_memdiag.zone_largest = 0;
    r19_memdiag.min_zone_free = 65535u;
    r19_memdiag.min_zone_largest = 65535u;
    r19_memdiag.stack_gap = r19_gap(sp);
    r19_memdiag.min_stack_gap = r19_memdiag.stack_gap;
    r19_memdiag.zone_bad = 0;
    r19_memdiag.stack_warning = 0;
    frame_counter = 0;
    watermark_begin = NULL;
    watermark_end = NULL;
    /* 512 bytes below current SP remain unmodified for interrupts/calls.
     * Never write in the static area at or below _bend. */
    if (sp > bend + 1024u)
    {
        watermark_begin = (volatile uint8_t *)(bend + 64u);
        watermark_end = (volatile uint8_t *)(sp - 512u);
        for (volatile uint8_t *p = watermark_begin; p < watermark_end; ++p)
            *p = 0xA5;
    }
    else r19_memdiag.stack_warning = 1;
    I_MemDiagSample();
}

void I_MemDiagSample(void)
{
    uintptr_t sp = r19_read_sp();
    uint16_t gap = r19_gap(sp);
    if (gap < r19_memdiag.min_stack_gap)
        r19_memdiag.min_stack_gap = gap;
    r19_memdiag.stack_gap = gap;
    /* Bounded scans every 16 completed frames, not in the VBlank ISR. */
    if ((frame_counter++ & 15u) != 0) return;

    uint16_t free_bytes = 0, largest = 0;
    uint8_t invalid = 0;
    Z_DiagSample(&free_bytes, &largest, &invalid);
    r19_memdiag.zone_free = free_bytes;
    r19_memdiag.zone_largest = largest;
    if (free_bytes < r19_memdiag.min_zone_free)
        r19_memdiag.min_zone_free = free_bytes;
    if (largest < r19_memdiag.min_zone_largest)
        r19_memdiag.min_zone_largest = largest;
    if (invalid) r19_memdiag.zone_bad = 1;

    if (watermark_begin)
    {
        volatile uint8_t *p = watermark_begin;
        while (p < watermark_end && *p == 0xA5) ++p;
        if (p < watermark_end)
        {
            uint16_t observed = r19_gap((uintptr_t)p);
            if (observed < r19_memdiag.min_stack_gap)
                r19_memdiag.min_stack_gap = observed;
        }
        if (watermark_begin[0] != 0xA5 || watermark_begin[16] != 0xA5)
            r19_memdiag.stack_warning = 1;
    }
    if (r19_memdiag.min_stack_gap < 256u)
        r19_memdiag.stack_warning = 1;
}
#endif
