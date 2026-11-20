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

#define VIEW_W   128               /* logical columns, each 2 screen pixels wide (H32: 256 px) */
#ifndef VIEW_H
#define VIEW_H   112               /* rows */
#endif
#define HALF_W   (VIEW_W / 2)
#define HORIZON  (VIEW_H / 2)
#define FOCAL    HALF_W            /* 90 degree horizontal field of view */
#ifndef VFOCAL
#define VFOCAL   128               /* vertical focal length in rows (column = ~2.3 rows wide on a 4:3 TV) */
#endif
#define FB_BYTES ((VIEW_W / 4) * VIEW_H * 4)

/* framebuffer layout = VDP tiles, column-major: tile column tc holds VIEW_H/8 tiles stacked,
 * a byte is a pair of 4bpp pixels, so logical column x is byte (x&3) of each 4-byte tile row. */
#define FB_COL(fb, x) ((fb) + (uint16_t)((uint16_t)((x) >> 2) * (uint16_t)(VIEW_H * 4)) + ((x) & 3))

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
