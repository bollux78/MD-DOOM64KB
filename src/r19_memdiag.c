/* R19 diagnostic: bounded zone walk, heap end-canary and read-only
 * 68000 stack-pointer sampling. No writes to the gap between _bend and SP:
 * SGDK may use that region for its own dynamic allocations.
 * The SP sample is not a true stack high-water mark.
 */
#include <stddef.h>
#include <stdint.h>
#include "compiler.h"
#include "r19_memdiag.h"
#include "z_zone.h"

#if defined(DOOM_MEM_DIAG)
extern uint8_t _bend; /* SGDK md.ld: first byte after static .data/.bss */
r19_memdiag_t r19_memdiag;
static uint16_t frame_counter;
extern uint8_t I_MemDiagHeapCanaryOK(void);

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
    uintptr_t sp = r19_read_sp();
    r19_memdiag.zone_free = 0;
    r19_memdiag.zone_largest = 0;
    r19_memdiag.min_zone_free = 65535u;
    r19_memdiag.min_zone_largest = 65535u;
    r19_memdiag.stack_gap = r19_gap(sp);
    r19_memdiag.min_stack_gap = r19_memdiag.stack_gap;
    r19_memdiag.zone_bad = 0;
    r19_memdiag.zone_guard_bad = 0;
    r19_memdiag.stack_warning = 0;
    frame_counter = 0;
    /* Only inspect RAM. Never fill unknown SGDK dynamic-memory areas. */
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

    if (!I_MemDiagHeapCanaryOK())
        r19_memdiag.zone_guard_bad = 1;

    if (r19_memdiag.min_stack_gap < 1024u)
        r19_memdiag.stack_warning = 1;
}
#endif
