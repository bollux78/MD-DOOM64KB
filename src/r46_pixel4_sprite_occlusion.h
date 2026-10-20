/* R46 M2C/P2E: native sprite column visibility, geometry-only.
 * All 76-column arrays belong to the future renderer, not static BSS.
 */
#ifndef R46_P4_SPRITE_OCCLUSION_H
#define R46_P4_SPRITE_OCCLUSION_H
#include <stdint.h>
#include "r46_pixel4_sprite_camera.h"
typedef struct {
    int16_t top, bottom; /* inclusive [0,43], valid only on success */
} r46_p4_sprite_post_t;
#if defined(DOOM_R46_M2C)
/* Wall occlusion is only applied when solid[x] is nonzero and wall_depth[x]
 * is nearer than the sprite. Depths are positive integer world units.
 * Otherwise ceiling/floor clip the visible sprite post. Caller owns arrays.
 * On rejection output is not modified. This is NOT a complete masked
 * sprite ordering implementation and does not handle portal depth sorting.
 */
uint16_t R46_P4_SpriteVisiblePost(uint16_t x,
    const r46_p4_sprite_rect_t *sprite,
    const int16_t ceilingclip[76],const int16_t floorclip[76],
    const uint8_t solid[76],const uint16_t wall_depth[76],
    r46_p4_sprite_post_t *out);
uint16_t R46_P4_SpriteOcclusionValidate(void);
#endif
#endif
