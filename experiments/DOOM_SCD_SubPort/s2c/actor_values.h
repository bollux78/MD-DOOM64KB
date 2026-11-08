#ifndef S2C_ACTOR_VALUES_H
#define S2C_ACTOR_VALUES_H
#include "globdata.h"
#include "r_main.h"
#include "i_system.h"
static inline uint32_t S2C_Mix(uint32_t h,uint32_t v){return (h^v)*16777619UL;}
static inline void S2C_Values(const mobj_t *m,uint16_t id,uint32_t v[13])
{
    v[0]=id;v[1]=m->type;v[2]=m->x;v[3]=m->y;v[4]=m->z;
    v[5]=m->angle;v[6]=m->flags;v[7]=m->state-states;
    v[8]=m->sprite;v[9]=m->frame;v[10]=(int32_t)m->health;v[11]=(int32_t)m->tics;
    v[12]=SUBSECTOR_SECTOR(m->subsector)-_g_sectors;
}
static inline void S2C_Write(volatile uint8_t *p,const uint32_t v[13])
{
    *(volatile uint16_t *)(p)=v[0];*(volatile uint16_t *)(p+2)=v[1];
    for(uint16_t j=0;j<5;j++)*(volatile uint32_t *)(p+4+j*4)=v[2+j];
    for(uint16_t j=0;j<6;j++)*(volatile uint16_t *)(p+24+j*2)=v[7+j];
}
extern uint16_t S2C_RomCount(void),S2C_RomDead(uint16_t),S2C_RomDelay(uint16_t);
extern void S2C_RomApply(uint16_t,uint16_t,uint16_t);
#endif
