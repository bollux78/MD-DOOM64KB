/* R60 P1 private ABI: assembled wall column, only precomposed-LUT path. */
#ifndef R60_PAIR_WALL_H
#define R60_PAIR_WALL_H
#include <stdint.h>
static inline __attribute__((always_inline)) void R60_WallDraw(uint8_t *dst,
    const uint8_t *src,const uint8_t *lut,uint16_t frac,uint16_t step,
    uint16_t count,uint16_t odd_head)
{
    register uint8_t *a0 __asm__("a0")=dst;
    register const uint8_t *a1 __asm__("a1")=src;
    register const uint8_t *a2 __asm__("a2")=lut;
    register uint32_t d0 __asm__("d0")=frac;
    register uint32_t d1 __asm__("d1")=step;
    register uint32_t d2 __asm__("d2")=count;
    register uint32_t d3 __asm__("d3")=odd_head;
    __asm__ volatile("jsr R60_WallColumn"
        : "+a"(a0),"+d"(d0),"+d"(d1),"+d"(d2),"+d"(d3)
        : "a"(a1),"a"(a2) : "d4","d5","d6","d7","cc","memory");
}
#endif
