#include <stdint.h>
#include "actors_wire.h"
#include "actor_values.h"
static mobj_t *live[S2C_MAX_ACTORS];
static uint16_t ids[S2C_MAX_ACTORS],nextid,romcount;
static uint32_t previous_rom[S2C_MAX_ROM];
static uint32_t used=256;
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
void S2C_Capture(uint16_t tic){
    uint16_t frame=tic/100u,n=0,playerid=0,nr=0;
    if(frame>=S2C_FRAME_COUNT || tic%100u)I_Error("S2C FRAME ORDER");
    if(!frame){
#if defined(SCD_LIVE)
        used=256;
#endif
        romcount=S2C_RomCount();if(romcount>S2C_MAX_ROM)I_Error("S2C ROM COUNT");
        for(uint16_t i=0;i<64;i++)HEAD[i]=0;
        HEAD[0]=S2C_MAGIC;HEAD[1]=1;HEAD[2]=S2C_FRAME_COUNT;HEAD[3]=romcount;HEAD[6]=36;
    }
    if(romcount!=S2C_RomCount())I_Error("S2C ROM COUNT CHANGED");
    for(uint16_t i=0;i<S2C_MAX_ACTORS;i++)if(live[i]){n++;if(live[i]==_g_player.mo)playerid=ids[i];}
    if(!playerid)I_Error("S2C PLAYER ID");
    HEAD[8+frame]=used;volatile uint8_t *header=reserve(16);
    uint32_t h=S2C_Mix(S2C_Mix(S2C_Mix(2166136261UL,n),romcount),playerid);
    for(uint16_t i=0;i<S2C_MAX_ACTORS;i++)if(live[i]){
        uint32_t v[13];S2C_Values(live[i],ids[i],v);
        for(uint16_t j=0;j<13;j++)h=S2C_Mix(h,v[j]);
        S2C_Write(reserve(36),v);
    }
    for(uint16_t i=0;i<romcount;i++){
        uint16_t dead=S2C_RomDead(i),delay=S2C_RomDelay(i);
        h=S2C_Mix(S2C_Mix(h,dead),delay);
        uint32_t v=((uint32_t)dead<<16)|delay;
        if(!frame || previous_rom[i]!=v){
            volatile uint16_t *p=(volatile uint16_t *)reserve(8);
            p[0]=i;p[1]=dead;p[2]=delay;p[3]=0;nr++;previous_rom[i]=v;
        }
    }
    *(volatile uint32_t *)header=tic;*(volatile uint16_t *)(header+4)=n;
    *(volatile uint16_t *)(header+6)=nr;*(volatile uint32_t *)(header+8)=h;
    *(volatile uint16_t *)(header+12)=playerid;*(volatile uint16_t *)(header+14)=0;
}
void S2C_Finish(void){
    HEAD[4]=used;HEAD[5]=0;uint32_t h=2166136261UL;
    for(uint32_t i=0;i<used;i++)h=S2C_Mix(h,BASE[i]);HEAD[5]=h;
}
