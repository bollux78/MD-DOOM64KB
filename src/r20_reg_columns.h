/* R20g private ABI. Only the inline wrapper may call the assembly entry. */
#ifndef R20_REG_COLUMNS_H
#define R20_REG_COLUMNS_H
#include <stdint.h>
extern uint16_t _s_screen[];
static inline __attribute__((always_inline)) void R20_RegDraw(uint16_t *dest,const uint8_t *src,const uint16_t *map,uint16_t frac,uint16_t step,uint16_t count) {
    register uint16_t *a0 __asm__("a0")=dest;
    register const uint8_t *a1 __asm__("a1")=src;
    register const uint16_t *a2 __asm__("a2")=map;
    register uint32_t d0 __asm__("d0")=frac;
    register uint32_t d1 __asm__("d1")=step;
    register uint32_t d2 __asm__("d2")=count-1;
    __asm__ volatile("jsr R20_RegColumn" : "+a"(a0),"+d"(d0),"+d"(d1),"+d"(d2)
        : "a"(a1),"a"(a2) : "d3","d4","d5","d6","d7","cc","memory");
}
#endif
