/* R46 M2C/P2G: mask arbitrary occluded rows within one sprite post.
 * 44 rows packed into low 44 bits of a 64-bit caller-owned mask.
 */
#ifndef R46_P4_SPRITE_MASK_H
#define R46_P4_SPRITE_MASK_H
#include <stdint.h>
#include "r46_pixel4_sprite_camera.h"
typedef void (*r46_p4_mask_emit_t)(uint16_t x,uint16_t y0,
                                   uint16_t y1,void *ctx);
#if defined(DOOM_R46_M2C)
/* Bit=1 means covered/occluded. Callback emits maximal runs of visible
 * rows in ascending y. Returns count of runs, 0 for fully occluded or
 * invalid arguments. Never touches the active 8x8 framebuffer. */
uint16_t R46_P4_EmitMaskedPosts(uint16_t x,
    const r46_p4_sprite_rect_t *sprite,uint64_t occluded_rows,
    r46_p4_mask_emit_t emit,void *ctx);
uint16_t R46_P4_SpriteMaskValidate(void);
#endif
#endif
