/* R68: per-frame workload log + PC sampler (diagnostic only). See r68_prof.h. */
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include <string.h>   /* after genesis.h: SGDK string.h needs u16/s32 types first */
#include "i_system.h"
#include "globdata.h"
#include "r68_prof.h"
#if defined(DOOM_R68_PROF)
#if !defined(HINTERRUPT_CALLBACK)
#error R68 sampler needs SGDK >= 1.80 (HInt vector jumps straight to the callback)
#endif
extern volatile uint32_t _g_vblankCount;
extern void R68_HInt(void);
r68_block_t *r68_ptr;

/* The assembler handler hard-codes these offsets. */
_Static_assert(offsetof(r68_block_t, ring) == 0, "R68 asm: ring must be first");
_Static_assert(offsetof(r68_block_t, head) == 2u * DOOM_R68_RING, "R68 asm: head offset");
_Static_assert(offsetof(r68_block_t, samples) == 2u * DOOM_R68_RING + 4u, "R68 asm: samples offset");
_Static_assert(offsetof(r68_block_t, bad) == 2u * DOOM_R68_RING + 8u, "R68 asm: bad offset");
_Static_assert(sizeof(r68_block_t) == 356, "R68 host reader expects 356 bytes");

void R68_Init(void)
{
    if (r68_ptr) return;
    r68_block_t *b = (r68_block_t *)MEM_alloc(sizeof(r68_block_t));
    if (!b) I_Error("R68 heap unavailable");
    memset(b, 0, sizeof(*b));
    b->magic = 0x52363850u;       /* 'R68P' */
    b->version = 1;
    b->ring_n = DOOM_R68_RING;
    r68_ptr = b;
}

void R68_Start(void)
{
    if (!r68_ptr) return;
    r68_ptr->head = 0;
    r68_ptr->samples = 0;
    SYS_setHIntCallback(R68_HInt);
    VDP_setHIntCounter(DOOM_R68_LINES - 1);
    VDP_setHInterrupt(TRUE);
}

void R68_Mark(uint8_t k)
{
    r68_block_t *b = r68_ptr; if (!b) return;
    uint32_t vb; uint16_t v;
    do { vb = _g_vblankCount; v = *(volatile uint16_t *)0xC00008; } while (vb != _g_vblankCount);
    b->marks[k & 7] = (vb << 8) | (uint32_t)(v >> 8);
}

void R68_FrameBegin(void)
{
    r68_block_t *b = r68_ptr; if (!b) return;
    b->vb_start = _g_vblankCount;
    b->tic_start = _g_gametic;
    R68_Mark(0);
}

void R68_LogicDone(void)
{
    r68_block_t *b = r68_ptr; if (!b) return;
    b->vb_logic = _g_vblankCount;
    R68_Mark(1);
}

__attribute__((noinline)) void R68_FrameMark(void)
{
    __asm__ volatile ("" ::: "memory");   /* the host breaks here and reads r68_ptr */
}

void R68_FrameEnd(void)
{
    r68_block_t *b = r68_ptr; if (!b) return;
    b->vb_end = _g_vblankCount;
    b->tic_end = _g_gametic;
    R68_Mark(7);
    R68_FrameMark();
    /* host has read the record: clear ring + counters, count the next frame */
    b->head = 0;
    b->samples = 0;
    memset(b->c, 0, sizeof(b->c));
    memset(b->marks, 0, sizeof(b->marks));
    b->frame++;
}
#endif
