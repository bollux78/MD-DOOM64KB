/* Presentation proxies only: sector links rebuilt locally, no actor thinking,
 * collision links, targets or foreign native pointers. Original lists restored
 * before leaving replay. Storage resides in MD-owned Word RAM. */
#include <stddef.h>
#include <stdint.h>
#include "actors_wire.h"
#include "actor_values.h"
#include "i_system.h"
#define BASE ((volatile const uint8_t *)S2C_MD_BASE)
#define HEAD ((volatile const uint32_t *)S2C_MD_BASE)
#define POOL ((mobj_t *)S2C_MD_POOL)
#define SAVED_ROM ((uint32_t *)0x61C000UL)
#define SAVED_PLAYER ((int32_t *)0x61CC00UL)
#define SAVED_HEADS ((mobj_t **)0x61C800UL)
static uint16_t romcount;
void S2C_Begin(void){
    if(sizeof(mobj_t)*S2C_MAX_ACTORS>0x3000 || _g_numsectors>256)I_Error("S2C PROXY MEMORY");
    romcount=S2C_RomCount();uint32_t used=HEAD[4];
    if(HEAD[0]!=S2C_MAGIC || HEAD[1]!=1 || HEAD[2]!=S2C_FRAME_COUNT || HEAD[3]!=romcount ||
       romcount>S2C_MAX_ROM || HEAD[6]!=36 || used<256 || used>S2C_CAPACITY || used%4)I_Error("S2C HEADER");
#if !defined(SCD_FAST)
    uint32_t h=2166136261UL;
    for(uint32_t i=0;i<used;i++)h=S2C_Mix(h,(i>=20 && i<24)?0:BASE[i]);
    if(h!=HEAD[5])I_Error("S2C STREAM HASH");
#endif
    SAVED_PLAYER[0]=_g_player.mo->x;SAVED_PLAYER[1]=_g_player.mo->y;SAVED_PLAYER[2]=_g_player.mo->z;
    SAVED_PLAYER[3]=_g_player.mo->angle;SAVED_PLAYER[4]=_g_player.viewz;SAVED_PLAYER[5]=_g_player.health;
    SAVED_PLAYER[6]=_g_leveltime;
    for(uint16_t i=0;i<romcount;i++)SAVED_ROM[i]=((uint32_t)S2C_RomDead(i)<<16)|S2C_RomDelay(i);
    for(uint16_t i=0;i<_g_numsectors;i++)SAVED_HEADS[i]=_g_sectors[i].thinglist;
}
void S2C_End(void){
    _g_player.mo->x=SAVED_PLAYER[0];_g_player.mo->y=SAVED_PLAYER[1];_g_player.mo->z=SAVED_PLAYER[2];
    _g_player.mo->angle=SAVED_PLAYER[3];_g_player.viewz=SAVED_PLAYER[4];_g_player.health=SAVED_PLAYER[5];
    _g_player.mo->subsector=R_PointInSubsector(_g_player.mo->x,_g_player.mo->y);_g_leveltime=SAVED_PLAYER[6];
    for(uint16_t i=0;i<_g_numsectors;i++)_g_sectors[i].thinglist=SAVED_HEADS[i];
    for(uint16_t i=0;i<romcount;i++)S2C_RomApply(i,SAVED_ROM[i]>>16,SAVED_ROM[i]);
    *(volatile uint32_t *)0x61B0A0UL=1;
}
void S2C_ApplyFrame(uint16_t frame){
    if(frame>=S2C_FRAME_COUNT)I_Error("S2C FRAME INDEX");
    uint32_t off=HEAD[8+frame];
    if(off<256 || off%4 || off+16>HEAD[4])I_Error("S2C FRAME BOUNDS");
    volatile const uint8_t *p=BASE+off;
    uint32_t tic=*(volatile const uint32_t *)p,want=*(volatile const uint32_t *)(p+8);
    uint16_t n=*(volatile const uint16_t *)(p+4),nr=*(volatile const uint16_t *)(p+6),player=*(volatile const uint16_t *)(p+12);
    uint32_t end=off+16+(uint32_t)n*36+(uint32_t)nr*8;
    if(tic!=(uint32_t)frame*100 || !n || n>S2C_MAX_ACTORS || nr>romcount || end>HEAD[4] ||
       end!=(frame+1==S2C_FRAME_COUNT?HEAD[4]:HEAD[9+frame]))I_Error("S2C RECORD BOUNDS");
    for(uint16_t i=0;i<_g_numsectors;i++)_g_sectors[i].thinglist=0;
    p+=16;uint16_t ids[S2C_MAX_ACTORS],foundplayer=0,expected=0;
    for(uint16_t i=0;i<n;i++,p+=36){
        mobj_t *m=&POOL[i];uint8_t *z=(uint8_t *)m;for(uint16_t j=0;j<sizeof(*m);j++)z[j]=0;
        ids[i]=*(volatile const uint16_t *)p;
        if(!ids[i])I_Error("S2C ZERO ID");
        for(uint16_t j=0;j<i;j++)if(ids[j]==ids[i])I_Error("S2C DUPLICATE ID");
        m->type=*(volatile const uint16_t *)(p+2);
        if(m->type>=NUMMOBJTYPES)I_Error("S2C TYPE");
        m->x=*(volatile const int32_t *)(p+4);m->y=*(volatile const int32_t *)(p+8);m->z=*(volatile const int32_t *)(p+12);
        m->angle=*(volatile const uint32_t *)(p+16);m->flags=*(volatile const uint32_t *)(p+20);
        uint16_t state=*(volatile const uint16_t *)(p+24);if(state>=NUMSTATES)I_Error("S2C STATE");
        m->state=&states[state];m->sprite=*(volatile const uint16_t *)(p+26);m->frame=*(volatile const uint16_t *)(p+28);
        if(m->sprite>=NUMSPRITES)I_Error("S2C SPRITE");
        m->health=*(volatile const int16_t *)(p+30);m->tics=*(volatile const int16_t *)(p+32);
        m->subsector=R_PointInSubsector(m->x,m->y);
        uint16_t sector=*(volatile const uint16_t *)(p+34);
        if(sector>=_g_numsectors || SUBSECTOR_SECTOR(m->subsector)!=&_g_sectors[sector])I_Error("S2C SPATIAL SECTOR");
        m->floorz=m->dropoffz=_g_sectors[sector].floorheight;m->ceilingz=_g_sectors[sector].ceilingheight;
        MOBJ_SET_RADIUS(m,mobjinfo[m->type].radius);MOBJ_SET_HEIGHT(m,mobjinfo[m->type].height);
        if(!(m->flags&MF_NOSECTOR)){
            mobj_t **head=&_g_sectors[sector].thinglist;m->snext=*head;m->sprev=head;
            if(m->snext)m->snext->sprev=&m->snext;*head=m;expected++;
        }
        if(ids[i]==player)foundplayer++;
    }
    if(foundplayer!=1)I_Error("S2C PLAYER MEMBERSHIP");
    for(uint16_t i=0;i<nr;i++,p+=8){
        uint16_t id=*(volatile const uint16_t *)p,dead=*(volatile const uint16_t *)(p+2),delay=*(volatile const uint16_t *)(p+4);
        S2C_RomApply(id,dead,delay);
    }
    uint16_t linked=0;
    for(uint16_t s=0;s<_g_numsectors;s++){
        mobj_t **prev=&_g_sectors[s].thinglist;
        for(mobj_t *m=*prev;m;m=m->snext){
            if(++linked>n || m<POOL || m>=POOL+n || m->sprev!=prev || *prev!=m ||
               SUBSECTOR_SECTOR(m->subsector)!=&_g_sectors[s])I_Error("S2C SPATIAL LINKS");
            prev=&m->snext;
        }
    }
    if(linked!=expected)I_Error("S2C LINK COUNT");
    uint32_t h=S2C_Mix(S2C_Mix(S2C_Mix(2166136261UL,n),romcount),player);
    for(uint16_t i=0;i<n;i++){
        uint32_t v[13];S2C_Values(&POOL[i],ids[i],v);
        for(uint16_t j=0;j<13;j++)h=S2C_Mix(h,v[j]);
        S2C_Write((volatile uint8_t *)(S2C_MD_APPLIED+(uint32_t)i*36),v);
    }
    for(uint16_t i=0;i<romcount;i++)h=S2C_Mix(S2C_Mix(h,S2C_RomDead(i)),S2C_RomDelay(i));
    if(h!=want)I_Error("S2C APPLIED ACTOR HASH");
    volatile uint32_t *r=(volatile uint32_t *)S2C_MD_REPORT;
    r[0]=want;r[1]=h;r[2]=n;r[3]=player;r[4]=nr;r[5]=linked;r[6]=sizeof(mobj_t);r[7]=offsetof(mobj_t,snext);r[8]=offsetof(mobj_t,sprev);
    r[9]=offsetof(mobj_t,subsector);r[10]=sizeof(sector_t);r[11]=offsetof(sector_t,thinglist);
}
