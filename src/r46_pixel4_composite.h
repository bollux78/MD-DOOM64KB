/* R46 M2C/P2I: offline composition of native geometry into 4bpp.
 * The caller owns the target, 44 row starts and sprite order; not a
 * video switch, VDP uploader or active R39f drawing path.
 */
#ifndef R46_P4_COMPOSITE_H
#define R46_P4_COMPOSITE_H
#include <stdint.h>
#include "r46_pixel4_pipeline.h"
#include "r46_pixel4_raster.h"
typedef struct {
    uint16_t plane_spans;
    uint16_t sprite_posts;
} r46_p4_composite_stats_t;
#if defined(DOOM_R46_M2C)
/* Render using flat palette indices (not authentic Doom textures).
 * count=0 permits null sprite inputs. keep_rows reserves y<keep_rows;
 * 2 reserves gameplay topbar. Reject invalid input before touching target.
 */
uint16_t R46_P4_ComposePreview(uint8_t *target,uint16_t capacity,
    const r46_p4_plane_window_t *plane,uint8_t starts[44],
    uint8_t background,uint8_t plane_color,uint16_t keep_rows,
    const r46_p4_sprite_rect_t *sprites,const uint16_t *depth,
    const uint8_t *sprite_colors,uint16_t count,uint8_t *indices,
    r46_p4_mask_lookup_t lookup,void *lookup_ctx,
    r46_p4_composite_stats_t *stats);
uint16_t R46_P4_CompositeValidate(void);
#endif
#endif
