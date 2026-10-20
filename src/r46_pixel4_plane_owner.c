/* R46 M2C/P2B: guarded native visplane window and contiguous BSP runs.
 * All buffers supplied by caller, no active 8x8 renderer state touched.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_plane_owner.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error R46 native plane owner requires M2B, no active R22 pixel4
#endif
_Static_assert(R46_P4_PLANE_WIDTH==76 && R46_P4_PLANE_HEIGHT==44,
               "native plane geometry drift");
void R46_P4_PlaneInit(r46_p4_plane_window_t *p)
{
    if(!p)return;
    for(uint16_t x=0;x<78;x++){p->top[x]=0xffu;p->bottom[x]=0;}
    p->minx=76;p->maxx=-1;
}
uint16_t R46_P4_PlaneJoin(r46_p4_plane_window_t *p,
                          int16_t start,int16_t stop)
{
    if(!p||start<0||stop>=76||start>stop)return 0;
    if(p->minx==76&&p->maxx==-1){p->minx=start;p->maxx=stop;return 1;}
    if(p->minx<0||p->maxx>=76||p->minx>p->maxx)return 0;
    int16_t left=p->minx>start?p->minx:start;
    int16_t right=p->maxx<stop?p->maxx:stop;
    for(int16_t x=left;x<=right;x++)
        if(p->top[x+1]!=0xffu)return 0;
    if(start<p->minx)p->minx=start;
    if(stop>p->maxx)p->maxx=stop;
    return 1;
}
uint16_t R46_P4_PlaneSetColumn(r46_p4_plane_window_t *p,
                               uint16_t x,uint8_t top,uint8_t bottom)
{
    if(!p||x>=76||top>=44||bottom>=44||top>bottom||
       x<(uint16_t)p->minx||x>(uint16_t)p->maxx)return 0;
    p->top[x+1]=top;
    p->bottom[x+1]=bottom;
    return 1;
}
uint16_t R46_P4_BSPOpenRuns(const uint8_t solid[76],
        uint16_t first,uint16_t stop,r46_p4_range_emit_t emit,void *ctx)
{
    if(!solid||!emit||first>=stop||stop>76)return 0;
    uint16_t n=0,x=first;
    while(x<stop){
        while(x<stop&&solid[x])x++;
        if(x==stop)break;
        uint16_t left=x;
        while(x<stop&&!solid[x])x++;
        emit(left,x,ctx);n++;
    }
    return n;
}
__attribute__((noinline))
uint16_t R46_P4_PlaneOwnerValidate(void)
{
    /* Only geometry metadata; no scratch or framebuffer is accessed. */
    return (uint16_t)(R46_P4_PLANE_WIDTH==76 && R46_P4_PLANE_HEIGHT==44 &&
       sizeof(r46_p4_plane_window_t)==160);
}
#endif
