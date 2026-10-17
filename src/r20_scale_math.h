/* R20e M3: exact low-word sine product and unsigned reciprocal.
 * Local to R_ScaleFromGlobalAngle; no global FixedMul/Div replacement.
 * GPL-2.0-or-later. */
#ifndef R20_SCALE_MATH_H
#define R20_SCALE_MATH_H
#include <stdint.h>
static inline int32_t R20_ScaleProduct(int16_t a, int32_t sine)
{
    /* sine has high word 0 or -1. Use unsigned corrections to define wrap. */
    uint16_t low = (uint16_t)sine;
    uint32_t r = (uint32_t)((int32_t)a * (int16_t)low);
    uint32_t upper = (uint32_t)(int32_t)a << 16;
    if (low & 0x8000u) r += upper;
    if (sine < 0) r -= upper;
    return (int32_t)r;
}
static const uint8_t r20_scale_bitlen[256] = {
#define R20B2(n) n,n
#define R20B4(n) R20B2(n),R20B2(n)
#define R20B8(n) R20B4(n),R20B4(n)
#define R20B16(n) R20B8(n),R20B8(n)
#define R20B32(n) R20B16(n),R20B16(n)
#define R20B64(n) R20B32(n),R20B32(n)
#define R20B128(n) R20B64(n),R20B64(n)
0,1,R20B2(2),R20B4(3),R20B8(4),R20B16(5),R20B32(6),R20B64(7),R20B128(8)
};
#undef R20B2
#undef R20B4
#undef R20B8
#undef R20B16
#undef R20B32
#undef R20B64
#undef R20B128
static inline uint32_t R20_ScaleMulu(uint16_t a, uint16_t b)
{
#if defined(__m68k__)
    uint32_t r = a;
    __asm__("mulu.w %1,%0" : "+&d"(r) : "d"(b) : "cc");
    return r;
#else
    return (uint32_t)a * b;
#endif
}
static inline uint32_t R20_ScaleReciprocal(uint32_t d)
{
    /* Precondition d != 0, same as the original quotient. Small divisors
       remain on libgcc; game uses this helper only for d >= 2^20. */
    if (d < 0x10000u) return 0xffffffffu / d;
    uint16_t top = (uint16_t)(d >> 16);
    uint8_t shift = (top >> 8) ? (uint8_t)(r20_scale_bitlen[top >> 8] + 8)
                              : r20_scale_bitlen[top];
    uint32_t q = 0xffffffffu >> shift;
    uint16_t dv = (uint16_t)(d >> shift);
#if defined(__m68k__)
    __asm__("divu.w %1,%0" : "+&d"(q) : "d"(dv) : "cc");
    q &= 0xffffu;
#else
    q /= dv;
#endif
    uint32_t low = R20_ScaleMulu((uint16_t)q, (uint16_t)d);
    uint32_t high = R20_ScaleMulu((uint16_t)q, (uint16_t)(d >> 16));
    if ((high >> 16) || low + (high << 16) < low) --q;
    return q;
}
#endif
