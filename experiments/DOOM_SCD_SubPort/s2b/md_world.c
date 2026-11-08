/* Apply visual values to native MD sectors/SRAM sides. Local AI/tickers are
 * never run; original pointer relationships and actor list remain local. */
#include <stddef.h>
#include <stdint.h>
#include "world_wire.h"
#include "world_values.h"
#include "i_system.h"
#include "w_wad.h"
extern void P_UpdateAnimatedFlat(void);
#define BASE ((volatile const uint8_t *)S2B_MD_WORLD)
#define HEAD ((volatile const uint32_t *)S2B_MD_WORLD)
static uint16_t nsec,nside;
void S2B_Init(void)
{
    nsec=_g_numsectors;nside=W_LumpLength(W_GetNumForName("E1M1")+3)/sizeof(mapsidedef_t);
    uint32_t used=HEAD[5];
    if(HEAD[0]!=S2B_MAGIC || HEAD[1]!=1 || HEAD[2]!=S2B_COUNT || HEAD[3]!=nsec ||
       HEAD[4]!=nside || used<256 || used>S2B_CAPACITY || used%4)I_Error("S2B HEADER COUNTS");
#if !defined(SCD_FAST)
    uint32_t h=2166136261UL;
    for(uint32_t i=0;i<used;i++)h=S2B_Mix(h,(i>=24 && i<28)?0:BASE[i]);
    if(h!=HEAD[6])I_Error("S2B STREAM HASH");
#endif
}
void S2B_ApplyFrame(uint16_t frame)
{
    if(frame>=S2B_COUNT)I_Error("S2B FRAME INDEX");
    uint32_t offset=HEAD[8+frame];
    if(offset<256 || offset+16>HEAD[5] || offset%4)I_Error("S2B FRAME BOUNDS");
    volatile const uint8_t *p=BASE+offset;
    uint32_t tic=*(volatile const uint32_t *)p;
    uint16_t ns=*(volatile const uint16_t *)(p+4),nd=*(volatile const uint16_t *)(p+6);
    uint32_t want=*(volatile const uint32_t *)(p+8);
    _g_leveltime=*(volatile const uint32_t *)(p+12);
    uint32_t end=offset+16+(uint32_t)ns*16+(uint32_t)nd*12;
    if(tic!=(uint32_t)frame*100 || ns>nsec || nd>nside || end>HEAD[5] ||
       (frame+1<S2B_COUNT && end!=HEAD[9+frame]) || (frame+1==S2B_COUNT && end!=HEAD[5]))I_Error("S2B RECORD BOUNDS");
    p+=16;
    for(uint16_t j=0;j<ns;j++,p+=16){
        uint16_t id=*(volatile const uint16_t *)p;
        if(id>=nsec)I_Error("S2B SECTOR ID");
        sector_t *s=&_g_sectors[id];
        s->lightlevel=*(volatile const int16_t *)(p+2);
        s->floorheight=*(volatile const int32_t *)(p+4);s->ceilingheight=*(volatile const int32_t *)(p+8);
        s->floorpic=*(volatile const int16_t *)(p+12);s->ceilingpic=*(volatile const int16_t *)(p+14);
    }
    for(uint16_t j=0;j<nd;j++,p+=12){
        uint16_t id=*(volatile const uint16_t *)p;
        if(id>=nside)I_Error("S2B SIDE ID");
        side_t *s=&_g_sides[id];
        R23_SET(s,textureoffset,*(volatile const int16_t *)(p+2));
        R23_SET(s,toptexture,*(volatile const int16_t *)(p+4));
        R23_SET(s,bottomtexture,*(volatile const int16_t *)(p+6));
        R23_SET(s,midtexture,*(volatile const int16_t *)(p+8));
    }
    uint16_t checked=1;
#if defined(SCD_FAST)
    extern volatile uint8_t s2e_test_deep;
    checked=s2e_test_deep || !(*(volatile const uint32_t *)0x61A008UL&31u);
#endif
    uint32_t h=0;
    if(checked){
    h=S2B_Mix(S2B_Mix(2166136261UL,nsec),nside);
    for(uint16_t i=0;i<nsec;i++){uint32_t v[5];S2B_SectorValues(i,v);for(uint16_t j=0;j<5;j++)h=S2B_Mix(h,v[j]);}
    for(uint16_t i=0;i<nside;i++){uint32_t v[4];S2B_SideValues(i,v);for(uint16_t j=0;j<4;j++)h=S2B_Mix(h,v[j]);}
    if(h!=want)I_Error("S2B APPLIED WORLD HASH");
    }
    P_UpdateAnimatedFlat(); /* renderer animation state, not simulation */
    volatile uint32_t *r=(volatile uint32_t *)S2B_MD_REPORT;
    r[0]=want;r[1]=h;r[2]=ns;r[3]=nd;r[4]=_g_leveltime;r[5]=checked;
}
