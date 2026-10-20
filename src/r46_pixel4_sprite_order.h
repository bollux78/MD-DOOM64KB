/* R46 M2C/P2G: deterministic far-to-near sprite ordering.
 * Caller owns both input depth array and index output; no static memory.
 */
#ifndef R46_P4_SPRITE_ORDER_H
#define R46_P4_SPRITE_ORDER_H
#include <stdint.h>
#if defined(DOOM_R46_M2C)
/* Stable descending depths; equality retains original insertion order.
 * Reject 0/invalid count or null pointers without writing output.
 * Depths are positive integral view-space units. Maximum 128 elements
 * keeps a bounded O(n^2) insertion pass while preserving no heap usage.
 */
uint16_t R46_P4_SortSprites(const uint16_t *depth,
    uint16_t count,uint8_t *indices);
uint16_t R46_P4_SpriteOrderValidate(void);
#endif
#endif
