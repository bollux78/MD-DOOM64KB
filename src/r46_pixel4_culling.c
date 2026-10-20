/* R46 M2C/P1: reusable 4x4 visplane/BSP/sprite scalar geometry.
 * Original Doom 8x8 clipping arrays stay untouched. The 76-column P4
 * data is supplied by the future renderer owner, not static globals.
 * No WAD, SGDK, VDP, heap, BSP traversal or IRQ calls occur here.
 */
#if defined(DOOM_R46_M2C)
#include <stdint.h>
#include "r46_pixel4_culling.h"
#if !defined(DOOM_R46_M2B) || !defined(DOOM_R46_M2A) || defined(DOOM_R22_PIXEL4)
#error R46 M2C needs the co-linked native 76x44 geometry alongside active R39f cell
#endif
_Static_assert(R46_P4_COLS==76 && R46_P4_SAMPLE_ROWS==44,"R46 native geometry drift");
_Static_assert(R46_P4_SPRITE_FRACTION_BITS==7,"R46 sprite COLEXTRABITS drift");

/* Identical overlap test to R_CheckPlane: if no used top[x] appears in
 * intersection of old/new horizontal ranges, the plane can be extended.
 * Invalid intervals are rejected before array reads. */
uint16_t R46_P4_PlaneCanExtend(const uint8_t top[76],
            int16_t minx,int16_t maxx,int16_t start,int16_t stop)
{
    if(!top || start<0 || stop>=R46_P4_COLS || start>stop)return 0;
    if(minx==R46_P4_COLS && maxx==-1)return 1; /* empty initial plane */
    if(minx<0 || maxx>=R46_P4_COLS || minx>maxx)return 0;
    const int16_t left=(minx>start)?minx:start;
    const int16_t right=(maxx<stop)?maxx:stop;
    for(int16_t x=left;x<=right;x++)
        if(top[x]!=0xffu)return 0;
    return 1;
}
uint16_t R46_P4_BSPAnyOpen(const uint8_t solid[76],uint16_t left,uint16_t right)
{
    if(!solid || left>=right || right>R46_P4_COLS)return 0;
    for(uint16_t x=left;x<right;x++)
        if(solid[x]==0)return 1;
    return 0;
}
uint16_t R46_P4_SpriteBounds(int16_t *x1,int16_t *x2,uint16_t gameplay)
{
    if(!x1 || !x2)return 0;
    int16_t left=*x1,right=*x2;
    const int16_t border=gameplay?2:0;
    if(right<left || left>=R46_P4_COLS || right<border)return 0;
    if(left<border)left=border;
    if(right>=R46_P4_COLS)right=R46_P4_COLS-1;
    if(left>right)return 0;
    *x1=left;*x2=right;
    return 1;
}
uint16_t R46_P4_SpriteDepth(uint32_t tz,uint32_t *scale,uint16_t *fracstep)
{
    if(!scale||!fracstep || tz<(4UL<<16) || tz>(1280UL<<16))return 0;
    const uint32_t worlddepth=tz>>16;
    if(!worlddepth)return 0;
    const uint32_t s=(44UL<<16)/worlddepth;
    const uint32_t step=tz/(44UL<<R46_P4_SPRITE_FRACTION_BITS);
    if(step>65535UL)return 0;
    *scale=s;*fracstep=(uint16_t)step;
    return 1;
}

static const r46_p4_culling_ops_t r46_p4_culling_ops={
    R46_P4_PlaneCanExtend,
    R46_P4_BSPAnyOpen,
    R46_P4_SpriteBounds,
    R46_P4_SpriteDepth
};
__attribute__((noinline))
const r46_p4_culling_ops_t *R46_P4_CullingOps(void)
{
    return &r46_p4_culling_ops;
}
__attribute__((noinline))
uint16_t R46_P4_CullingValidate(void)
{
    const r46_p4_culling_ops_t *o=R46_P4_CullingOps();
    return (uint16_t)(o&&o->plane_can_extend&&o->bsp_any_open&&
        o->sprite_bounds&&o->sprite_depth&&R46_P4_COLS==76&&
        R46_P4_SAMPLE_ROWS==44&&R46_P4_CENTER_X==38&&R46_P4_CENTER_Y==22);
}
#endif
