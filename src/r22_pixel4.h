/* R22 own packed 4x4 framebuffer primitives. GPL-2.0-or-later. */
#ifndef R22_PIXEL4_H
#define R22_PIXEL4_H
#include <stdint.h>
#define R22_W 76
#define R22_H 44
#define R22_PITCH 38
#define R22_FB_BYTES (R22_PITCH * R22_H)
#define R22_TILES 836
/* 2 independent horizontal samples per byte. */
static inline void R22_Put(uint8_t *p,uint16_t x,uint16_t y,uint8_t c) {
    uint8_t *d=p+y*R22_PITCH+(x>>1); c&=15;
    *d=(x&1)?(uint8_t)((*d&240)|c):(uint8_t)((*d&15)|(c<<4));
}
static inline uint32_t R22_ExpandPair(uint8_t p) {
    return ((uint32_t)(p>>4)*0x11110000u)|((uint32_t)(p&15)*0x1111u);
}
#endif
