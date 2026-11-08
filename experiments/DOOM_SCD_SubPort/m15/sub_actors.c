#include <stdint.h>
#include "actors_wire.h"
#include "compact.h"
static mobj_t *live[S2C_MAX_ACTORS];
static uint16_t ids[S2C_MAX_ACTORS],nextid,romcount;
static uint32_t previous_rom[S2C_MAX_ROM];
static uint8_t dirty_rom[S2C_MAX_ROM];
static uint16_t initialized;
extern void S2F_ClockPoll(void);
static uint32_t used=256;
#if defined(SCD_FAST)
static uint16_t captured;
#endif
#define BASE ((volatile uint8_t *)S2C_SUB_BASE)
#define HEAD ((volatile uint32_t *)S2C_SUB_BASE)
void S2C_ResetActors(void){for(uint16_t i=0;i<S2C_MAX_ACTORS;i++)live[i]=0;}
void S2C_ActorSpawn(mobj_t *m){
    if(nextid==65535)I_Error("S2C ID EXHAUSTED");
    for(uint16_t i=0;i<S2C_MAX_ACTORS;i++)if(!live[i]){live[i]=m;ids[i]=++nextid;return;}
    I_Error("S2C LIVE ACTOR LIMIT");
}
void S2C_ActorRemove(mobj_t *m){
    for(uint16_t i=0;i<S2C_MAX_ACTORS;i++)if(live[i]==m){live[i]=0;return;}
    I_Error("S2C REMOVE UNKNOWN ID");
}
static volatile uint8_t *reserve(uint16_t n){
    if(used+n>S2C_CAPACITY)I_Error("S2C ACTOR STREAM FULL");
    volatile uint8_t *p=BASE+used;used+=n;return p;
}
static sector_t *sector_keys[512],*sector_base;
static uint16_t sector_ids[512];
static void sector_index_init(void){
 if(sector_base==_g_sectors)return;sector_base=_g_sectors;
 for(uint16_t i=0;i<512;i++)sector_keys[i]=0;
 sector_t *s=_g_sectors;
 for(uint16_t i=0;i<_g_numsectors;i++,s++){uint16_t k=((uint32_t)s>>2)&511u;while(sector_keys[k])k=(k+1)&511u;sector_keys[k]=s;sector_ids[k]=i;}
}
uint16_t M15_SectorIndex(sector_t *s){uint16_t k=((uint32_t)s>>2)&511u;while(sector_keys[k] && sector_keys[k]!=s)k=(k+1)&511u;if(!sector_keys[k])I_Error("M15 ACTOR SECTOR");return sector_ids[k];}
/* Reject only clearly rear-facing sprites; no visibility/occlusion test.
 * Rounded octants and a generous margin avoid multiplication and keep edges. */
static uint16_t relevant(const mobj_t *m){
 if(m==_g_player.mo)return 1;
 if(m->sprite<0 || m->sprite>=NUMSPRITES)return 0;
 fixed_t dx=m->x-_g_player.mo->x,dy=m->y-_g_player.mo->y;
 fixed_t ax=dx<0?-dx:dx,ay=dy<0?-dy:dy;
 if(ax>1280L*FRACUNIT || ay>1280L*FRACUNIT)return 0;
 return 1;
}
void S2C_Capture(uint16_t tic){
    uint16_t frame=tic/100u,n=0,playerid=0,nr=0,eligible[64];
    sector_index_init();
#if defined(SCD_FAST)
    const uint16_t full=!captured;
#else
    const uint16_t full=!frame;
#endif
    if(frame>=S2C_FRAME_COUNT || tic%100u)I_Error("S2C FRAME ORDER");
    if(!frame){
#if defined(SCD_LIVE)
        used=256;
#endif
        romcount=S2C_RomCount();if(romcount>S2C_MAX_ROM)I_Error("S2C ROM COUNT");
        for(uint16_t i=0;i<64;i++)HEAD[i]=0;
        HEAD[0]=S2C_MAGIC;HEAD[1]=2;HEAD[2]=S2C_FRAME_COUNT;HEAD[3]=romcount;HEAD[6]=24;
    }
    if(romcount!=S2C_RomCount())I_Error("S2C ROM COUNT CHANGED");
    uint16_t all=0;
    for(uint16_t i=0;i<S2C_MAX_ACTORS;i++)if(live[i]){all++;if(relevant(live[i])){eligible[n++]=i;if(live[i]==_g_player.mo)playerid=ids[i];}}
    HEAD[7]=all;
    if(!playerid)I_Error("S2C PLAYER ID");
    HEAD[8+frame]=used;volatile uint8_t *header=reserve(16);
    uint32_t h=M15_Mix(M15_Mix(M15_Mix(2166136261UL,n),romcount),playerid);
    for(uint16_t j=0;j<n;j++){
        uint16_t i=eligible[j];S2F_ClockPoll();uint32_t v[10];M15_Values(live[i],ids[i],v);
        for(uint16_t j=0;j<10;j++)h=M15_Mix(h,v[j]);
        M15_Write(reserve(24),v);
    }
    for(uint16_t i=0;i<romcount;i++){
        uint16_t dead=S2C_RomDead(i),delay=S2C_RomDelay(i);
        h=M15_Mix(M15_Mix(h,dead),delay);
        uint32_t v=((uint32_t)dead<<16)|delay;
        if(initialized && previous_rom[i]!=v)dirty_rom[i]=1;
        previous_rom[i]=v;
        if(full || dirty_rom[i]){
            volatile uint16_t *p=(volatile uint16_t *)reserve(8);
            p[0]=i;p[1]=dead;p[2]=delay;p[3]=0;nr++;
        }
    }
#if defined(SCD_FAST)
    initialized=1;
#endif
    *(volatile uint32_t *)header=tic;*(volatile uint16_t *)(header+4)=n;
    *(volatile uint16_t *)(header+6)=nr;*(volatile uint32_t *)(header+8)=h;
    *(volatile uint16_t *)(header+12)=playerid;*(volatile uint16_t *)(header+14)=0;
}
void S2C_Finish(void){
    HEAD[4]=used;HEAD[5]=0;
#if defined(SCD_FAST)
    return; /* complete packet checksum is checked before application */
#endif
    uint32_t h=2166136261UL;
    for(uint32_t i=0;i<used;i++)h=M15_Mix(h,BASE[i]);HEAD[5]=h;
}


void M15_ActorsDelivered(void){captured=1;}
