/* N2 function profiler without interrupts: renderer files are built with -finstrument-functions;
 * every entry/exit charges the sub stopwatch ticks (30.72 us, 12-bit) since the previous event
 * to the function on top of a shadow stack (exclusive time; statistically fair at tick edges). */
#include <stdint.h>
#define NF 512
typedef struct { uint32_t fn, units, calls; } ProfEntry;
ProfEntry scd_prof_tab[NF];
uint8_t scd_prof_enabled;
static uint32_t stack_fn[96];
static int16_t depth;
static uint16_t last;

#define NI __attribute__((no_instrument_function))
static NI uint16_t now(void) { return *(volatile const uint16_t *)0xFF800CUL & 0xFFF; }
static NI ProfEntry *slot(uint32_t fn)
{
    uint16_t h = (uint16_t)(fn >> 1) & (NF - 1);
    for (uint16_t n = 0; n < NF; n++, h = (h + 1) & (NF - 1))
        if (scd_prof_tab[h].fn == fn || !scd_prof_tab[h].fn) { scd_prof_tab[h].fn = fn; return &scd_prof_tab[h]; }
    return &scd_prof_tab[0];
}
static NI void charge(void)
{
    const uint16_t t = now();
    const uint16_t d = (uint16_t)(t - last) & 0xFFF;
    last = t;
    slot(depth > 0 && depth <= 96 ? stack_fn[depth - 1] : 1)->units += d;
}
NI void scd_prof_start(void) { depth = 0; last = now(); scd_prof_enabled = 1; }
NI void scd_prof_stop(void) { if (scd_prof_enabled) charge(); scd_prof_enabled = 0; }
NI void __cyg_profile_func_enter(void *fn, void *site)
{
    if (!scd_prof_enabled) return;
    charge();
    if (depth < 96) stack_fn[depth] = (uint32_t)fn;
    depth++;
    slot((uint32_t)fn)->calls++;
}
NI void __cyg_profile_func_exit(void *fn, void *site)
{
    if (!scd_prof_enabled) return;
    charge();
    if (depth > 0) depth--;
}
