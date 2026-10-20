/* R46 M2C/P1 native geometry helpers.
 * Pure functions and caller-owned clip/visplane buffers, zero extra BSS.
 * Geometry stays R39f 38x22 until a later verified dispatcher.
 */
#ifndef R46_P4_CULLING_H
#define R46_P4_CULLING_H
#include <stdint.h>
enum {
    R46_P4_COLS = 76,
    R46_P4_SAMPLE_ROWS = 44,
    R46_P4_CENTER_X = 38,
    R46_P4_CENTER_Y = 22,
    R46_P4_SPRITE_FRACTION_BITS = 7,
    R46_P4_BSP_TOTAL_SOLID_BYTES = 76,
    R46_P4_VISPLANE_TOP_BYTES = 76
};
#if defined(DOOM_R46_M2C)
/* 1 if a visplane may extend its span, 0 if a duplicate is needed.
 * Top[] corresponds to drawable columns 0..75, with unused == 0xFF.
 * Does not allocate or mutate any memory. */
uint16_t R46_P4_PlaneCanExtend(const uint8_t top[76],
            int16_t minx,int16_t maxx,int16_t start,int16_t stop);
/* 1 if any x in [left,right) remains unoccluded. Unlike memchr,
 * invalid intervals are rejected before looking at solid[].
 * solid[x] == 0 means a visible gap. */
uint16_t R46_P4_BSPAnyOpen(const uint8_t solid[76],uint16_t left,uint16_t right);
/* Clip projected inclusive sprite bounds, respecting border for gameplay.
 * Rejected segments do not change either endpoint. */
uint16_t R46_P4_SpriteBounds(int16_t *x1,int16_t *x2,uint16_t gameplay);
/* Same initial sprite scale and fracstep relationships as r_draw.c,
 * specialized to 44 pixel rows (COLEXTRABITS=7). This does not calculate
 * camera/world coordinates, z clipping or weapon/psprite transforms. */
uint16_t R46_P4_SpriteDepth(uint32_t tz,uint32_t *scale,uint16_t *fracstep);
typedef struct {
    uint16_t (*plane_can_extend)(const uint8_t *,int16_t,int16_t,int16_t,int16_t);
    uint16_t (*bsp_any_open)(const uint8_t *,uint16_t,uint16_t);
    uint16_t (*sprite_bounds)(int16_t *,int16_t *,uint16_t);
    uint16_t (*sprite_depth)(uint32_t,uint32_t *,uint16_t *);
} r46_p4_culling_ops_t;
const r46_p4_culling_ops_t *R46_P4_CullingOps(void);
uint16_t R46_P4_CullingValidate(void);
#endif
#endif
