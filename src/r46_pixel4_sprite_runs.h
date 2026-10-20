/* R46 M2C/P2F: caller-owned native masked sprite post emitter.
 * No new framebuffer, drawseg array, heap, persistent storage or VDP state.
 */
#ifndef R46_P4_SPRITE_RUNS_H
#define R46_P4_SPRITE_RUNS_H
#include <stdint.h>
#include "r46_pixel4_sprite_occlusion.h"
typedef void (*r46_p4_sprite_post_emit_t)(uint16_t x,
    int16_t first_y,int16_t last_y,void *ctx);
#if defined(DOOM_R46_M2C)
/* Scan inclusive sprite rectangle in ascending columns. Emit one clipped
 * contiguous post per visible column, with no scratch allocation.
 * Reject invalid rectangles and null arrays before emitting anything.
 * Returns number of emitted columns (0 is also a valid empty result).
 * Important: this only handles one clipped post per projected column;
 * multi-window masked drawseg and translucent sprite spans remain future.
 */
uint16_t R46_P4_EmitSpritePosts(const r46_p4_sprite_rect_t *sprite,
    const int16_t ceilingclip[76],const int16_t floorclip[76],
    const uint8_t solid[76],const uint16_t wall_depth[76],
    r46_p4_sprite_post_emit_t emit,void *ctx);
uint16_t R46_P4_SpriteRunsValidate(void);
#endif
#endif
