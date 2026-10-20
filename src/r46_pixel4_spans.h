/* R46 M2C/P2A: native 76x44 span and solid-column state.
 * Caller owns all 44 row starts and 76 occlusion entries. This module
 * never touches the active 8x8 renderer, framebuffer, VDP or allocator.
 */
#ifndef R46_PIXEL4_SPANS_H
#define R46_PIXEL4_SPANS_H
#include <stdint.h>
enum { R46_P4_SPAN_COLS=76, R46_P4_SPAN_ROWS=44 };
typedef void (*r46_p4_span_emit_t)(uint16_t y,uint16_t x1,uint16_t x2,void *ctx);
#if defined(DOOM_R46_M2C)
void R46_P4_SpansClear(uint8_t starts[44],uint8_t solid[76]);
/* Inclusive vertical intervals; 44 is the empty sentinel for t,
 * while t>b denotes an empty interval. x is in 0..76 and may be 76
 * for the closing boundary; the callback sees valid x1..x2<76. */
uint16_t R46_P4_MakeSpans(uint8_t starts[44],uint16_t x,
    uint16_t t1,uint16_t b1,uint16_t t2,uint16_t b2,
    r46_p4_span_emit_t emit,void *ctx);
/* Solid interval [first,stop), clipped to 0..76. Returns new columns. */
uint16_t R46_P4_MarkSolid(uint8_t solid[76],int16_t first,int16_t stop);
uint16_t R46_P4_SpansValidate(void);
#endif
#endif
