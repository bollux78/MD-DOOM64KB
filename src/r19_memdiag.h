/* R19 isolated memory diagnostic. Do not include in production R18 builds. */
#ifndef R19_MEMDIAG_H
#define R19_MEMDIAG_H
#include <stdint.h>
#if defined(DOOM_MEM_DIAG)
typedef struct {
    uint16_t zone_free;
    uint16_t zone_largest;
    uint16_t min_zone_free;
    uint16_t min_zone_largest;
    uint16_t stack_gap;
    uint16_t min_stack_gap;
    uint8_t zone_bad;
    uint8_t zone_guard_bad;
    uint8_t stack_warning;
} r19_memdiag_t;
extern r19_memdiag_t r19_memdiag;
void I_MemDiagInit(void);
void I_MemDiagSample(void);
#endif
#endif
