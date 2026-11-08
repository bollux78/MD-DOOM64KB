/* Real sub world snapshots, independent of renderer. Fixed reserved stream;
 * no zone allocations or copied engine structs/pointers. */
#include <stdint.h>
#include "world_wire.h"
#include "world_values.h"
#include "w_wad.h"
#include "i_system.h"
static uint32_t prev_sector[S2B_MAX_SECTORS][4];
static uint32_t prev_side[S2B_MAX_SIDES][2];
static uint32_t used=256;
static uint16_t nsec,nside;
#if defined(SCD_FAST)
static uint16_t captured;
#endif
#define BASE ((volatile uint8_t *)S2B_SUB_WORLD)
#define HEAD ((volatile uint32_t *)S2B_SUB_WORLD)
static volatile uint8_t *reserve(uint16_t n)
{
    if(used+n>S2B_CAPACITY)I_Error("S2B WORLD STREAM FULL");
    volatile uint8_t *p=BASE+used;used+=n;return p;
}
void S2B_Capture(uint16_t tic)
{
    const uint16_t frame=tic/100u;
#if defined(SCD_FAST)
    const uint16_t full=!captured;
#else
    const uint16_t full=!frame;
#endif
    if(frame>=S2B_COUNT || tic%100u)I_Error("S2B FRAME ORDER");
    if(frame==0){
#if defined(SCD_LIVE)
        used=256;
#endif
        nsec=_g_numsectors;
        nside=W_LumpLength(W_GetNumForName("E1M1")+3)/sizeof(mapsidedef_t);
        if(!nsec || nsec>S2B_MAX_SECTORS || !nside || nside>S2B_MAX_SIDES)I_Error("S2B WORLD COUNTS");
        for(uint16_t i=0;i<64;i++)HEAD[i]=0;
        HEAD[0]=S2B_MAGIC;HEAD[1]=S2B_VERSION;HEAD[2]=S2B_COUNT;HEAD[3]=nsec;HEAD[4]=nside;
    }
    HEAD[8+frame]=used;
    volatile uint8_t *header=reserve(16);
    uint32_t h=S2B_Mix(S2B_Mix(2166136261UL,nsec),nside);
    uint16_t ns=0,nd=0;
    for(uint16_t i=0;i<nsec;i++){
        uint32_t v[5];S2B_SectorValues(i,v);
        for(uint16_t j=0;j<5;j++)h=S2B_Mix(h,v[j]);
        uint32_t packed=((uint32_t)(uint16_t)v[2]<<16)|(uint16_t)v[3];
        if(full || prev_sector[i][0]!=v[0] || prev_sector[i][1]!=v[1] ||
           prev_sector[i][2]!=packed || prev_sector[i][3]!=v[4]){
            volatile uint8_t *p=reserve(16);
            *(volatile uint16_t *)(p+0)=i;*(volatile uint16_t *)(p+2)=v[4];
            *(volatile uint32_t *)(p+4)=v[0];*(volatile uint32_t *)(p+8)=v[1];
            *(volatile uint16_t *)(p+12)=v[2];*(volatile uint16_t *)(p+14)=v[3];
#if !defined(SCD_M15)
            prev_sector[i][0]=v[0];prev_sector[i][1]=v[1];prev_sector[i][2]=packed;prev_sector[i][3]=v[4];
#endif
            ns++;
        }
    }
    for(uint16_t i=0;i<nside;i++){
        uint32_t v[4];S2B_SideValues(i,v);
        for(uint16_t j=0;j<4;j++)h=S2B_Mix(h,v[j]);
        uint32_t a=((uint32_t)(uint16_t)v[0]<<16)|((uint32_t)(uint8_t)v[1]<<8)|(uint8_t)v[2];
        uint32_t b=(uint8_t)v[3];
        if(full || prev_side[i][0]!=a || prev_side[i][1]!=b){
            volatile uint8_t *p=reserve(12);
            *(volatile uint16_t *)(p+0)=i;
            for(uint16_t j=0;j<4;j++)*(volatile uint16_t *)(p+2+j*2)=v[j];
            *(volatile uint16_t *)(p+10)=0;
#if !defined(SCD_M15)
            prev_side[i][0]=a;prev_side[i][1]=b;
#endif
            nd++;
        }
    }
    *(volatile uint32_t *)(header+0)=tic;
    *(volatile uint16_t *)(header+4)=ns;*(volatile uint16_t *)(header+6)=nd;
#if defined(SCD_FAST) && !defined(SCD_M15)
    captured=1;
#endif
    *(volatile uint32_t *)(header+8)=h;*(volatile uint32_t *)(header+12)=_g_leveltime;
}
void S2B_Finish(void)
{
    HEAD[5]=used;HEAD[6]=0;
#if defined(SCD_FAST)
    return; /* one checked outer packet covers these bytes */
#endif
    uint32_t h=2166136261UL;
    for(uint32_t i=0;i<used;i++)h=S2B_Mix(h,BASE[i]);
    HEAD[6]=h;
}


#if defined(SCD_M15)
/* Commit the delivered snapshot, never the possibly newer live world. */
void M15_WorldDelivered(void){
 volatile const uint8_t *p=BASE+256;
 uint16_t ns=*(volatile const uint16_t *)(p+4),nd=*(volatile const uint16_t *)(p+6);p+=16;
 for(uint16_t j=0;j<ns;j++,p+=16){uint16_t i=*(volatile const uint16_t *)p;
  prev_sector[i][0]=*(volatile const uint32_t *)(p+4);prev_sector[i][1]=*(volatile const uint32_t *)(p+8);
  prev_sector[i][2]=((uint32_t)*(volatile const uint16_t *)(p+12)<<16)|*(volatile const uint16_t *)(p+14);
  prev_sector[i][3]=(int32_t)*(volatile const int16_t *)(p+2);
 }
 for(uint16_t j=0;j<nd;j++,p+=12){uint16_t i=*(volatile const uint16_t *)p;
  prev_side[i][0]=((uint32_t)*(volatile const uint16_t *)(p+2)<<16)|((uint32_t)(uint8_t)*(volatile const uint16_t *)(p+4)<<8)|(uint8_t)*(volatile const uint16_t *)(p+6);
  prev_side[i][1]=(uint8_t)*(volatile const uint16_t *)(p+8);
 }
 captured=1;
}
#endif
