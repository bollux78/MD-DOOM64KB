/* R46 M2C/P2D: actor world-to-camera projection, Q16.16.
 * Pure helper, caller-owned output, no VDP/heap/WAD/renderer state.
 */
#ifndef R46_P4_SPRITE_WORLD_H
#define R46_P4_SPRITE_WORLD_H
#include <stdint.h>
#include "r46_pixel4_sprite_camera.h"
typedef struct {
    int32_t depth;    /* camera forward coordinate, Q16.16 */
    int32_t lateral;  /* camera right coordinate, Q16.16 */
} r46_p4_sprite_camera_point_t;
#if defined(DOOM_R46_M2C)
/* cos/sin are fixed Q16.16 values supplied by view-angle tables.
 * Reject overflow instead of wrapping; no write on rejection. */
uint16_t R46_P4_WorldToCamera(int32_t actor_x,int32_t actor_y,
    int32_t view_x,int32_t view_y,int32_t viewcos,int32_t viewsin,
    r46_p4_sprite_camera_point_t *out);
/* The left edge/height offsets are already patch-relative, in world Q16.
 * This helper does NOT select rotations, patches or texture columns. */
uint16_t R46_P4_ProjectWorldSprite(int32_t actor_x,int32_t actor_y,
    int32_t view_x,int32_t view_y,int32_t viewcos,int32_t viewsin,
    int32_t patch_left,int32_t patch_width,
    int32_t top_z,int32_t bottom_z,uint16_t gameplay,
    r46_p4_sprite_rect_t *out);
uint16_t R46_P4_WorldSpriteValidate(void);
#endif
#endif
