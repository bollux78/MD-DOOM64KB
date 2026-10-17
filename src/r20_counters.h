/* R20 C0: per-run event counters for the DEMO3 timedemo (diagnostic only).
 * Off unless DOOM_R20_COUNTERS is defined. The counting itself costs CPU:
 * never compare the FPS of a counters ROM with a performance ROM.
 * GPL-2.0-or-later. */
#ifndef R20_COUNTERS_H
#define R20_COUNTERS_H
#include <stdint.h>
#if defined(DOOM_R20_COUNTERS)
enum
{
    R20C_TEX_CALLS,      /* R_DrawColumnSprite calls with count > 0      */
    R20C_TEX_CELLS,      /* cells written by those calls                 */
    R20C_FLAT_CALLS,     /* R_DrawColumnFlat calls with count > 0        */
    R20C_FLAT_CELLS,
    R20C_WALL_SIMPLE,    /* wall columns: 1 patch, not overlapped        */
    R20C_WALL_MULTI,     /* wall columns: several patches, not overlapped */
    R20C_WALL_COMPOSITE, /* wall columns through R_ComposeColumn         */
    R20C_TAN3,           /* seg-loop columns using the 16-bit tangent    */
    R20C_TAN4,           /* seg-loop columns using the 32-bit tangent    */
    R20C_SEGS,           /* R_StoreWallRange reaching R_RenderSegLoop    */
    R20C_SIGHT,          /* P_CheckSight calls                           */
    R20C_SIGHT_DEPTH,    /* max pending far sides (needs R20 S2)         */
    R20C_SEGCOLS,        /* R21: every R_RenderSegLoop column            */
    R20C_TEX_SKIP,       /* R21: segtextured columns with no tier/masked */
    R20C_N
};
extern uint32_t r20_cnt[R20C_N];
#define R20_COUNT(i, n) (r20_cnt[(i)] += (uint32_t)(n))
#define R20_MAX(i, v)   do { if ((uint32_t)(v) > r20_cnt[(i)]) r20_cnt[(i)] = (uint32_t)(v); } while (0)
#else
#define R20_COUNT(i, n) ((void)0)
#define R20_MAX(i, v)   ((void)0)
#endif
#endif
