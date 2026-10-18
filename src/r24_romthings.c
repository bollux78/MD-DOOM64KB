#include "compiler.h"
#include "globdata.h"
#include "r24_romthings.h"
#if defined(DOOM_R24_EPISODE)
#include "z_zone.h"
#include "m_random.h"
#include "p_inter.h"
#include "i_system.h"
#include "r24_static_types.h"
int16_t r24_start_map=1;
typedef struct {uint16_t thing,subsector,type,cell;} romthing_t;
static const romthing_t *records;
static const mapthing_t *mapthings;
static const uint16_t *thingmap,*celloffs,*cellidx,*secoffs,*secidx;
static uint8_t *removed;
static uint16_t *delays;
static uint16_t count,current;
static mobj_t *proxy;
static int dead(uint16_t i){return removed[i>>3]&(1u<<(i&7));}
void R24_InitThings(int16_t map,int16_t lump){
    char name[9];mapthings=W_GetLumpByNum(lump);
    sprintf(name,"S%dRTHING",map);int16_t n=W_GetNumForName(name);records=W_GetLumpByNum(n);count=W_LumpLength(n)/sizeof(*records);
    sprintf(name,"S%dRMAP",map);thingmap=W_GetLumpByName(name);
    sprintf(name,"S%dCOFF",map);celloffs=W_GetLumpByName(name);
    sprintf(name,"S%dCIDX",map);cellidx=W_GetLumpByName(name);
    sprintf(name,"S%dROFF",map);secoffs=W_GetLumpByName(name);
    sprintf(name,"S%dRIDX",map);secidx=W_GetLumpByName(name);
    removed=Z_CallocLevel((count+7)/8);delays=Z_CallocLevel(count*sizeof(*delays));proxy=Z_CallocLevel(sizeof(*proxy));
}
int R24_IsRomThing(uint16_t i){return thingmap[i]!=0;}
int R24_SpawnRomThing(uint16_t i,const mapthing_t *mt){
    if(!thingmap[i])return 0;
    uint16_t id=thingmap[i]-1;const mobjinfo_t *info=&mobjinfo[records[id].type];
    int bit=_g_gameskill<=sk_easy?1:_g_gameskill==sk_medium?2:4;
    if(!(mt->options&bit)){removed[id>>3]|=1u<<(id&7);return 1;}
    P_Random(); /* P_SpawnMobj compatibility RNG call, same source order. */
    int16_t tics=states[info->spawnstate].tics;
    if(tics>0)delays[id]=1+P_Random()%tics;
    if(info->flags&MF_COUNTITEM)_g_totalitems++;
    return 1;
}
static mobj_t *make(uint16_t id){
    if(dead(id))return NULL;
    current=id;const romthing_t *r=&records[id];const mapthing_t *mt=&mapthings[r->thing];const mobjinfo_t *info=&mobjinfo[r->type];
    proxy->type=r->type;proxy->x=(int32_t)mt->x*FRACUNIT;proxy->y=(int32_t)mt->y*FRACUNIT;
    proxy->subsector=&_g_subsectors[r->subsector];sector_t *sec=SUBSECTOR_SECTOR(proxy->subsector);
    proxy->z=proxy->floorz=proxy->dropoffz=sec->floorheight;proxy->ceilingz=sec->ceilingheight;
    MOBJ_SET_RADIUS(proxy,info->radius);MOBJ_SET_HEIGHT(proxy,info->height);
    proxy->flags=info->flags;proxy->health=info->spawnhealth;proxy->angle=ANG45*mt->angle;
    if(mt->options&8)proxy->flags|=MF_AMBUSH;
    const state_t *state=&states[info->spawnstate];uint32_t elapsed=_g_leveltime;
    if(state->tics>0 && elapsed>=delays[id]){
        elapsed-=delays[id];state=&states[state->nextstate];
        uint16_t period=r24_periods[r->type];if(period)elapsed%=period;
        while(state->tics>0 && elapsed>=(uint16_t)state->tics){elapsed-=state->tics;state=&states[state->nextstate];}
    }
    proxy->state=state;proxy->sprite=state->sprite;proxy->frame=state->frame;proxy->tics=state->tics;
    return proxy;
}
int R24_RemoveRomThing(mobj_t *thing){
    if(thing!=proxy)return 0;
    removed[current>>3]|=1u<<(current&7);return 1;
}
boolean R24_BlockIterator(int16_t x,int16_t y,boolean (*func)(mobj_t*)){
    if(x<0||y<0||x>=_g_bmapwidth||y>=_g_bmapheight)return true;
    uint16_t cell=y*_g_bmapwidth+x;
    for(uint16_t i=celloffs[cell];i<celloffs[cell+1];i++){
        uint16_t id=cellidx[i];if(!(mobjinfo[records[id].type].flags&MF_SPECIAL))continue;
        mobj_t *thing=make(id);if(thing && !func(thing))return false;
    }
    return true;
}
void R24_ProjectSector(sector_t *sec,int16_t light,void (*project)(mobj_t*,int16_t)){
    uint16_t s=sec->sector_index;
    for(uint16_t i=secoffs[s];i<secoffs[s+1];i++){mobj_t *thing=make(secidx[i]);if(thing)project(thing,light);}
}
void R24_ValidateThings(void){
#if defined(DOOM_R23_CPU_PROBE)
    for(uint16_t i=0;i<count;i++){
        mobj_t *thing=make(i);if(!thing)continue;
        if(R_PointInSubsector(thing->x,thing->y)!=thing->subsector)I_Error("ROM THING BSP MISMATCH");
        if(thing->flags&(MF_SOLID|MF_SHOOTABLE|MF_COUNTKILL))I_Error("ROM THING DYNAMIC FLAGS");
        if(mapthings[records[i].thing].type==2007){
            int16_t before=_g_player.ammo[am_clip];_g_player.ammo[am_clip]=0;thing->z=_g_player.mo->z;
            P_TouchSpecialThing(thing,_g_player.mo);
            if(!dead(i) || !_g_player.ammo[am_clip])I_Error("ROM ITEM PICKUP FAILED");
            _g_player.ammo[am_clip]=before;
            return;
        }
    }
#endif
}
#endif
