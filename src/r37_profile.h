/* R37 render-work telemetry; only enabled in the playable profiling ROM.
 * Exact per-frame event counts, not CPU-cycle timings. GPL-2.0-or-later. */
#ifndef R37_PROFILE_H
#define R37_PROFILE_H

enum {
    R37_NODES = 0,         /* internal BSP nodes visited */
    R37_BBOX = 1,          /* back-subtree bounding boxes tested */
    R37_BBOX_FOV = 2,      /* bbox rejected before solid-column occlusion */
    R37_BBOX_OCCLUDED = 3, /* bbox fully hidden by closer solid columns */
    R37_SUBSECTORS = 4,    /* BSP leaf subsectors visited */
    R37_SEGS = 5,          /* segments handed to R_AddLine */
    R37_SEG_EARLY = 6,     /* backface, clipped FOV or zero-width segs */
    R37_WALL_RANGES = 7,   /* actually visible R_StoreWallRange calls */
    R37_COLUMNS = 8,       /* iterations of R_RenderSegLoop */
    R37_FLATS = 9,         /* visible floor/ceiling vertical column runs */
    R37_TEXTURES = 10,    /* textured wall/sprite column calls */
    R37_SKY = 11,         /* sky column runs */
    R37_COUNTER_COUNT = 12
};

#if defined(DOOM_R37_BSP_PROFILE)
#include <stdint.h>
extern volatile uint16_t r37_counts[R37_COUNTER_COUNT];
#define R37_HIT(which) (++r37_counts[(which)])
#else
#define R37_HIT(which) ((void)0)
#endif
#endif
