#ifndef M15_COMPACT_H
#define M15_COMPACT_H
#include <stdint.h>
#include "actor_values.h"
#define M15_MAGIC 0x53324D35UL
#define M15_STRIDE 24u
static inline uint32_t M15_Mix(uint32_t h,uint32_t x){return (((h<<5)|(h>>27))^x)+0x9e3779b9UL;}
static inline uint32_t M15_Check(volatile const uint32_t *p,uint16_t words){uint32_t h=2166136261UL;while(words--)h=M15_Mix(h,*p++);return h;}
static inline uint8_t M15_Flags(uint32_t f){return (f&15u)|((f>>12)&16u)|((f>>13)&32u)|((f>>14)&64u)|((f>>15)&128u);}
static inline uint32_t M15_Expand(uint8_t f){return (f&15u)|((uint32_t)(f&16u)<<12)|((uint32_t)(f&32u)<<13)|((uint32_t)(f&64u)<<14)|((uint32_t)(f&128u)<<15);}
static inline void M15_Values(const mobj_t *m,uint16_t id,uint32_t v[10]){
 v[0]=id;v[1]=m->type;v[2]=m->x;v[3]=m->y;v[4]=m->z;v[5]=m->angle>>24;v[6]=M15_Flags(m->flags);v[7]=m->sprite;v[8]=m->frame;v[9]=SUBSECTOR_SECTOR(m->subsector)-_g_sectors;
}
static inline void M15_Write(volatile uint8_t *p,uint32_t v[10]){
 *(volatile uint16_t *)p=v[0];*(volatile uint16_t *)(p+2)=v[1];
 *(volatile uint32_t *)(p+4)=v[2];*(volatile uint32_t *)(p+8)=v[3];*(volatile uint32_t *)(p+12)=v[4];
 p[16]=v[5];p[17]=v[6];*(volatile uint16_t *)(p+18)=v[7];*(volatile uint16_t *)(p+20)=v[8];*(volatile uint16_t *)(p+22)=v[9];
}
#endif
