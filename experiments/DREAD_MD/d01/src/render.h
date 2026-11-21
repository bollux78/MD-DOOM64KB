#ifndef RENDER_H
#define RENDER_H
#ifdef SGDK_GCC
#include <types.h>   /* SGDK provides the intN_t names */
typedef long long dread_i64;   /* SGDK 2.x has no int64_t, newer ones typedef it */
#define int64_t dread_i64
#else
#include <stdint.h>
#endif
#include "mapdata.h"

/* screen modes, switchable at run time (detail levels; 320x144 in H40, 256x144 in H32):
 *   row-doubled  (COLB 1): W x 72 logical pixels of 2 screen pixels, each row shown twice by per-line vscroll
 *   column-doubled (COLB 2): W/2 x 144 logical pixels of 4 screen pixels                                   */
#define VW_MAX   160
#define VH_MAX   144
#define FB_MAX   (40 * 144 * 4)                 /* bytes: the largest mode (H40 column-doubled) */
extern uint16_t r_vw, r_vh, r_colb, r_halfw, r_focal, r_horizon, r_vfocal, r_zppk, r_tcols, r_fbbytes;
extern uint16_t r_colofs[VW_MAX];               /* byte offset of each logical column in the framebuffer */
#ifdef DREAD_ROW_ONLY
#define COLB     1
#else
#define COLB     r_colb
#endif
#define VIEW_W   r_vw
#define VIEW_H   r_vh
#define HALF_W   r_halfw
#define HORIZON  r_horizon
#define FOCAL    r_focal            /* 90 degrees over the full screen width (side crop keeps it) */
#define VFOCAL   r_vfocal
#define FB_TCOLS r_tcols
#define FB_BYTES r_fbbytes
/* framebuffer layout = VDP tiles, column-major: tile column tc holds VIEW_H/8 tiles stacked,
 * a byte is a pair of 4bpp pixels; logical column x starts at byte x*COLB of the 4-byte tile rows. */
#define FB_COL(fb, x) ((fb) + r_colofs[x])
void R_SetMode(uint16_t colb, uint16_t tcols, uint16_t crop);  /* tcols = 40 (H40) or 32 (H32), crop = tiles removed per side */

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
