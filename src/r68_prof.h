/* R68: per-frame workload log + statistical PC sampler (DIAGNOSTIC ONLY, BlastEm).
 * Everything lives in one small SGDK-heap block (no cartridge SRAM, no big BSS):
 *   - 128-entry ring of PC>>3 samples taken by the horizontal interrupt;
 *   - the record of the frame that has just finished (vblank stamps + counters).
 * The host (scripts/lab/r68_capture.py) breaks at R68_FrameMark() once per game
 * frame over the GDB RSP, reads the block, and the ROM then clears ring and counters.
 * GPL-2.0-or-later. */
#ifndef R68_PROF_H
#define R68_PROF_H
#include <stdint.h>

#if defined(DOOM_R68_PROF)
#define DOOM_R68_RING 128          /* samples kept per frame; excess is counted, not stored.
                                    * r68_prof_hint.s hard-codes 128: change both together. */
#ifndef DOOM_R68_LINES
#define DOOM_R68_LINES 48          /* one HInt every 48 active lines */
#endif

enum {
    R68_BSPNODE,   /* BSP nodes visited */
    R68_BBOX,      /* R_CheckBBox calls */
    R68_ADDLINE,   /* R_AddLine calls */
    R68_SEG,       /* R_StoreWallRange calls (visible segs) */
    R68_COL,       /* R_RenderSegLoop column iterations */
    R68_WALL,      /* R42_DrawPackedWall calls */
    R68_FLAT,      /* R_DrawColumnFlat calls */
    R68_PTA,       /* R_PointToAngle16 calls */
    R68_SPRPROJ,   /* R_ProjectSprite calls */
    R68_SPRDRAW,   /* R_DrawSprite calls */
    R68_SIGHT,     /* P_CheckSight calls */
    R68_SPARE,
    R68_N
};

typedef struct {
    uint16_t ring[DOOM_R68_RING];  /* PC>>3 (0xFFFF = beyond 512 KiB) */
    uint16_t head;                 /* entries stored this frame */
    uint16_t pad;
    uint32_t samples;              /* HInt samples this frame, stored or not */
    uint32_t bad;                  /* HInt frames with an unexpected stack layout */
    uint32_t magic;                /* 'R68P' */
    uint16_t version;              /* 1 */
    uint16_t ring_n;
    uint32_t frame;                /* index of the frame this record describes */
    uint32_t vb_start, vb_logic, vb_end;
    int32_t  tic_start, tic_end;
    uint16_t c[R68_N];
} r68_block_t;

extern r68_block_t *r68_ptr;
#define R68_HIT(k) do { r68_block_t *b68_ = r68_ptr; if (b68_) b68_->c[k]++; } while (0)
void R68_Init(void);          /* allocate and clear the block (once) */
void R68_Start(void);         /* arm the sampler (DEMO3 start) */
void R68_FrameBegin(void);
void R68_LogicDone(void);
void R68_FrameEnd(void);      /* publish the record, call R68_FrameMark, clear */
void R68_FrameMark(void);     /* the host's breakpoint */
#else
#define R68_HIT(k) ((void)0)
#endif
#endif
