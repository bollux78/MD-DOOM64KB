/* R46 M2B vertical coordinate/clip logic, independent of R39f 8x8.
 * Standalone R44 ASM still owns the reference 76x44 gameplay behavior.
 * No mutable globals, no VDP accesses and no duplicate 76-column arrays.
 */
#if defined(DOOM_R46_M2B)
#include <stdint.h>
#include "r46_pixel4_vertical.h"
#if !defined(DOOM_R46_M2A) || !defined(DOOM_R46_M1B) || defined(DOOM_R22_PIXEL4)
#error R46 M2B requires co-linked M2A projection with 8x8 still active
#endif
_Static_assert(R46_P4_VW==76 && R46_P4_VH==44 && R46_P4_VCY==22,
               "R44 native framebuffer geometry unexpectedly changed");
_Static_assert(R46_P4_CLIP_BYTES==304,"R46 two clip planes changed");

void R46_P4_InitOpeningClips(int16_t floorclip[76],int16_t ceilingclip[76],
                             uint16_t reserve_topbar)
{
    if(!floorclip || !ceilingclip)return;
    int16_t ceiling=reserve_topbar?0:-1;
    for(uint16_t x=0;x<R46_P4_VW;x++){
        floorclip[x]=R46_P4_VH;
        ceilingclip[x]=ceiling;
    }
}
uint16_t R46_P4_ClipColumn(int16_t x,int16_t *yl,int16_t *yh,uint16_t gameplay)
{
    if(!yl || !yh)return 0;
    int16_t first=*yl,last=*yh;
    const int16_t border=gameplay?R46_P4_BORDER:0;
    if(last<first || x<border || x>=R46_P4_VW)return 0;
    if(first<border)first=border;
    if(last>=R46_P4_VH)last=R46_P4_VH-1;
    if(first>last)return 0;
    *yl=first;*yh=last;
    return 1;
}
static const r46_p4_vertical_ops_t r46_p4_vertical_ops={
    R46_P4_InitOpeningClips,R46_P4_ClipColumn,R46_P4_VerticalValidate
};
__attribute__((noinline))
const r46_p4_vertical_ops_t *R46_P4_VerticalOps(void)
{
    return &r46_p4_vertical_ops;
}
__attribute__((noinline))
uint16_t R46_P4_VerticalValidate(void)
{
    const r46_p4_vertical_ops_t *ops=R46_P4_VerticalOps();
    if(!ops||!ops->init_opening_clips||!ops->clip_column||!ops->geometry_validate)
        return 0;
    /* No writes to the active 8x8 framebuffer or clip buffers at boot. */
    return (uint16_t)(R46_P4_VW==76 && R46_P4_VH==44
      && R46_P4_VCY==22 && R46_P4_CLIP_BYTES==304
      && R46_P4_TOPBAR==1 && R46_P4_BORDER==2);
}
#endif
