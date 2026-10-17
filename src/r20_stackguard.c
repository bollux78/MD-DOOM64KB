/* R20a: bounded, read-only heap inspection and painted stack watermark.
 * Diagnostic builds only. Peak includes startup since main, and saturates
 * at the reserve size. SP probes include their own instrumentation overhead.
 * GPL-2.0-or-later. */
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "r20_stackguard.h"
#if defined(DOOM_R20_STACKGUARD)
#if !defined(MEMORY_HIGH) || !defined(STACK_SIZE)
#error R20a requires the actual SGDK memory_base.h
#endif
#define PAINT 0x5AA5C33Cu
#define TOP ((uint32_t)MEMORY_HIGH + (uint32_t)STACK_SIZE)
extern uint8_t _bend;
volatile uint16_t r20_errors;
volatile uint32_t r20_first_error_tic, r20_min_sp;
uint16_t r20_peak, r20_sgdk_free = 65535, r20_sgdk_largest = 65535;
uint16_t r20_zone_free = 65535, r20_zone_largest = 65535;
static volatile uint8_t frozen;
static volatile uint32_t last_tic;
static void error(uint16_t bits, uint32_t tic)
{
    if (!bits) return;
    if (!r20_errors) r20_first_error_tic = tic;
    r20_errors |= bits;
}
void R20_StackPaint(void)
{
    uint32_t sp;
    SYS_disableInts();
    __asm__ volatile ("move.l %%sp,%0" : "=a" (sp));
    r20_min_sp = sp;
    volatile uint32_t *q = (volatile uint32_t*)MEMORY_HIGH;
    uint32_t limit = (sp - 64u) & ~3u;
    if (limit > TOP) limit = TOP;
    while ((uint32_t)q < limit) *q++ = PAINT;
    SYS_enableInts();
}
void R20_StackWatch(uint32_t tic)
{
    if (frozen) return;
    uint32_t sp;
    __asm__ volatile ("move.l %%sp,%0" : "=a" (sp));
    /* Called from main or VBlank; mask IRQs for the sticky first-event update. */
    uint16_t sr;
    __asm__ volatile ("move.w %%sr,%0\n\tori.w #0x700,%%sr" : "=d" (sr) : : "cc", "memory");
    last_tic = tic;
    if (sp < r20_min_sp) r20_min_sp = sp;
    uint16_t e = 0;
    if (*(volatile uint32_t*)MEMORY_HIGH != PAINT) e |= 1;
    if (*(volatile uint16_t*)(MEMORY_HIGH - 2) != 0) e |= 2;
    if (sp < (uint32_t)MEMORY_HIGH || sp >= TOP) e |= 8;
    error(e, tic);
    __asm__ volatile ("move.w %0,%%sr" : : "d" (sr) : "cc", "memory");
}
static uint8_t heap_probe(uint16_t *total, uint16_t *largest)
{
    uint32_t h = ((uint32_t)&_bend + 1u) & ~1u;
    const uint32_t end = (uint32_t)MEMORY_HIGH - 2u;
    uint32_t sum = 0, run = 0, best = 0;
    uint16_t steps = 0;
    if (h < (uint32_t)RAM || h >= end) return 1;
    while (h < end)
    {
        if (++steps > 8192u || (h & 1u)) return 1;
        uint16_t raw = *(volatile uint16_t*)h;
        uint16_t size = raw & 0xfffeu;
        if (size < 2u || size > end - h) return 1;
        if (!(raw & 1u)) { sum += size; run += size; if (run > best) best = run; }
        else run = 0;
        h += size;
    }
    if (h != end || *(volatile uint16_t*)end != 0) return 1;
    *total = (uint16_t)sum; *largest = (uint16_t)best;
    return 0;
}
void R20_DiagSample(void)
{
    if (frozen) return;
    SYS_disableInts();
    volatile const uint32_t *q = (volatile const uint32_t*)MEMORY_HIGH;
    while ((uint32_t)q < TOP && *q == PAINT) q++;
    r20_peak = (uint16_t)(TOP - (uint32_t)q);
    uint16_t total = 0, largest = 0;
    if (heap_probe(&total, &largest)) error(4, last_tic);
    else { if (total < r20_sgdk_free) r20_sgdk_free = total;
           if (largest < r20_sgdk_largest) r20_sgdk_largest = largest; }
    uint8_t bad = 0;
    Z_R20Probe(&total, &largest, &bad);
    if (bad) error(16, last_tic);
    else { if (total < r20_zone_free) r20_zone_free = total;
           if (largest < r20_zone_largest) r20_zone_largest = largest; }
    SYS_enableInts();
}
void R20_DiagFreeze(void)
{
    R20_DiagSample();
    frozen = 1; /* must precede VDP_init/text/result loops */
}
uint16_t R20_StackReserveBytes(void) { return (uint16_t)STACK_SIZE; }
#if defined(DOOM_R21_STACK_PLAY)
uint16_t r21_boot_peak;
void R21_StackRepaintForPlay(void)
{
    R20_DiagSample();               /* r20_peak = boot peak so far */
    r21_boot_peak = r20_peak;
    /* r20_min_sp remains the lifetime low-water mark; painted peak restarts below. */
    uint32_t sp;
    SYS_disableInts();
    __asm__ volatile ("move.l %%sp,%0" : "=a" (sp));
    volatile uint32_t *q = (volatile uint32_t*)MEMORY_HIGH;
    uint32_t limit = (sp - 64u) & ~3u;
    if (limit > TOP) limit = TOP;
    while ((uint32_t)q < limit) *q++ = PAINT;
    SYS_enableInts();
    R20_DiagSample();               /* r20_peak restarts at the live depth */
}
#endif
#endif
