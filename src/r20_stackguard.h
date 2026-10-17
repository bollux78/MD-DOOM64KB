/* R20a bounded memory diagnostic. GPL-2.0-or-later. */
#ifndef R20_STACKGUARD_H
#define R20_STACKGUARD_H
#include <stdint.h>
#if defined(DOOM_R20_STACKGUARD)
/* Error bits: 1 paint, 2 SGDK end marker, 4 SGDK chain, 8 SP, 16 Doom zone. */
extern volatile uint16_t r20_errors;
extern volatile uint32_t r20_first_error_tic;
extern volatile uint32_t r20_min_sp;
extern uint16_t r20_peak, r20_sgdk_free, r20_sgdk_largest;
extern uint16_t r20_zone_free, r20_zone_largest;
void R20_StackPaint(void);
void R20_StackWatch(uint32_t tic);
void R20_DiagSample(void);
void R20_DiagFreeze(void);
uint16_t R20_StackReserveBytes(void);
void Z_R20Probe(uint16_t*, uint16_t*, uint8_t*);
#define R20_PROBE() R20_StackWatch((uint32_t)_g_gametic)
#else
#define R20_PROBE() ((void)0)
#endif
#endif
