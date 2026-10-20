/* R46 M1: second native packed-4bpp renderer, no independent framebuffer.
 * Both renderers share the 2128-byte R20 tilemap backing. The caller MUST
 * own this storage exclusively while R46 P4 is active. No live switching,
 * VDP upload or clip/projection dispatch is implemented in M1.
 *
 * Do not confuse the R42 MC68000 packed-nibble store below with the 8x8
 * tile-word R20_REG_COLUMNS kernel. Those are incompatible layouts. */
#ifndef R46_P4_SECONDARY_H
#define R46_P4_SECONDARY_H
#include <stdint.h>
#include "r_defs.h"
#include "i_video.h"
typedef struct {
    uint16_t width;
    uint16_t height;
    uint16_t pitch;
    uint16_t frame_bytes;
    uint16_t backing_bytes;
    void (*clear)(void);
    void (*wall)(const draw_column_vars_t *);
    void (*sprite)(const draw_column_vars_t *);
    void (*flat)(uint8_t, const draw_column_vars_t *);
    uint32_t (*expand_pair)(uint8_t);
} r46_p4_ops_t;
#if defined(DOOM_R46_M1)
const r46_p4_ops_t *R46_P4_Ops(void);
uint16_t R46_P4_Validate(void);
#endif
#endif
