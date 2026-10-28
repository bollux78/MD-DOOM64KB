/* R47 exact 68000 multiplication helpers. GPL-2.0-or-later.
 * These helpers preserve the low 32-bit wraparound of libgcc __mulsi3 while
 * using native 16x16 MUL instructions where one operand is known 16-bit. */
#ifndef R47_MUL_H
#define R47_MUL_H
#include <stdint.h>

static inline uint32_t R47_Mulu16(uint16_t a,uint16_t b)
{
    uint32_t r=a;
    __asm__ volatile("mulu.w %1,%0" : "+d"(r) : "d"(b) : "cc");
    return r;
}
static inline int32_t R47_Muls16(int16_t a,int16_t b)
{
    int32_t r=a;
    __asm__ volatile("muls.w %1,%0" : "+d"(r) : "d"(b) : "cc");
    return r;
}
/* Exact low 32 bits of signed int32 x signed int16. */
static inline int32_t R47_Mul32x16(int32_t a,int16_t b)
{
    const uint16_t lo=(uint16_t)(uint32_t)a;
    const int16_t hi=(int16_t)((uint32_t)a>>16);
    uint32_t low=R47_Mulu16(lo,(uint16_t)b);
    if(b<0) low-=(uint32_t)lo<<16;
    const uint32_t high=(uint32_t)R47_Muls16(hi,b);
    return (int32_t)(low+(high<<16));
}
/* Exact low 32 bits for signed int16 x arbitrary uint32 bit pattern. */
static inline int32_t R47_Mul16xU32(int16_t a,uint32_t b)
{
    return R47_Mul32x16((int32_t)b,a);
}
#endif
