/* R46 M2C/P2H: integrates previously isolated geometry primitives.
 * Geometry pipeline only, NOT a drawable 4x4 renderer or VDP dispatcher.
 * Every buffer is caller owned; no permanent WRAM allocations.
 */
#ifndef R46_P4_PIPELINE_H
#define R46_P4_PIPELINE_H
#include <stdint.h>
#include "r46_pixel4_plane_owner.h"
#include "r46_pixel4_spans.h"
#include "r46_pixel4_sprite_mask.h"
#include "r46_pixel4_sprite_order.h"
#if defined(DOOM_R46_M2C)
/* Uses guarded 76-column plane window and 44-row span kernel.
 * Validates plane before any callback. Returns number of emitted spans.
 * The caller initializes row_starts[44] with 0xff; it is mutated.
 * Geometry-only path: callback is responsible for rasterization. */
uint16_t R46_P4_SweepPlane(const r46_p4_plane_window_t *plane,
    uint8_t row_starts[44],r46_p4_span_emit_t emit,void *ctx);

/* Sort caller-supplied rectangles back-to-front then emit each
 * visible masked post. The supplied mask callback returns 44 occlusion bits
 * at (sprite_id,x). No per-sprite or per-column static storage.
 * The index scratch capacity is count, max 128; caller owns it.
 * Rectangles can be invisible but MUST all be well formed to avoid partial
 * emission after a malformed late entry. Returns total post runs.
 * A return value of zero is also valid when everything is occluded. */
typedef uint64_t (*r46_p4_mask_lookup_t)(uint16_t sprite_id,
    uint16_t x,void *ctx);
typedef void (*r46_p4_pipeline_post_emit_t)(uint16_t sprite_id,
    uint16_t x,uint16_t y0,uint16_t y1,void *ctx);
uint16_t R46_P4_EmitOrderedSpriteScene(
    const r46_p4_sprite_rect_t *sprites,const uint16_t *depth,
    uint16_t count,uint8_t *order,r46_p4_mask_lookup_t mask_lookup,
    r46_p4_pipeline_post_emit_t emit,void *ctx);
uint16_t R46_P4_PipelineValidate(void);
#endif
#endif
