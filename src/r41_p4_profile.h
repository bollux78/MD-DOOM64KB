/* R41 Q1: statistical 4x4 renderer stage telemetry.
 * Only for pixel4 timedemo, never enabled in performance reference ROMs.
 * VBlank samples CPU stage 60 times/sec; it is NOT a cycle-exact profiler.
 * VBlank may be masked during VRAM uploads, undercounting that stage. */
#ifndef R41_P4_PROFILE_H
#define R41_P4_PROFILE_H
#include <stdint.h>
#if defined(DOOM_R41_P4_PROFILE)
enum { R41_P4_STAGES = 14 };
extern volatile uint16_t doom_profile_stage;
extern volatile uint16_t r41_p4_samples[R41_P4_STAGES];
extern volatile uint16_t r41_p4_total;
void R41_P4Reset(void);
void R41_P4Start(void);
#endif
#endif
