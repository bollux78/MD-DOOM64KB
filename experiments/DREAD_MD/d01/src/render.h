#ifndef RENDER_H
#define RENDER_H
#ifdef SGDK_GCC
#include <types.h>   /* SGDK provides the intN_t names */
#ifndef int64_t
#define int64_t long long
#endif
#else
#include <stdint.h>
#endif
#include "mapdata.h"

/* screen variants (H40, 320x144 on screen like Dread MD):
 *   default / ROWDUP: 160 columns x 72 rows, each row shown twice by per-line vertical scroll
 *   COLDUP (COLB=2): 80 columns of 4 pixels x 144 rows                                   */
#ifndef COLB
#define COLB     1                 /* bytes (pixel pairs) per logical column */
#endif
#ifndef VIEW_W
#define VIEW_W   (COLB == 2 ? 80 : 160)
#endif
#ifndef VIEW_H
#define VIEW_H   (COLB == 2 ? 144 : 72)
#endif
#define HALF_W   (VIEW_W / 2)
#define HORIZON  (VIEW_H / 2)
#define FOCAL    HALF_W            /* 90 degree horizontal field of view */
#ifndef VFOCAL
/* vertical focal in rows: logical pixel = 2*COLB H40 pixels (0.93 wide each) by (COLB==1 ? 2 : 1) lines */
#define VFOCAL   (COLB == 2 ? 179 : 90)          /* Doom's proportions: 160/200 of the screen height per unit */
#endif
#define FB_TCOLS (VIEW_W * COLB / 4)               /* tile columns */
#define FB_BYTES (FB_TCOLS * VIEW_H * 4)

/* framebuffer layout = VDP tiles, column-major: tile column tc holds VIEW_H/8 tiles stacked,
 * a byte is a pair of 4bpp pixels; logical column x starts at byte x*COLB of the 4-byte tile rows. */
#define FB_COL(fb, x) ((fb) + (uint16_t)((uint16_t)(((x) * COLB) >> 2) * (uint16_t)(VIEW_H * 4)) + (((x) * COLB) & 3))

typedef struct {
    int32_t x, y;                  /* 16.16 map units */
    int16_t z;                     /* eye height, map units */
    uint16_t angle;                /* 0..65535, 0 = east, counter-clockwise */
} View;

typedef struct {
    uint16_t segs_drawn, nodes_visited, cols_closed, subs_visited, col_visits, anchors;
} RenderStats;

extern MapSector map_sectors[];
extern RenderStats rstats;
extern const int16_t sintab[1024];   /* Q14 */

void R_Init(void);
void R_BuildNametable(uint16_t *nt, uint16_t tilebase);   /* TROWS x 32 entries */
void R_RenderView(const View *v, uint8_t *fb);
int  R_PointInSub(int16_t x, int16_t y);
#endif
