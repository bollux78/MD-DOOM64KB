/* Canonical semantic values; sector layout differs between CPUs, side fields
 * on MD must pass through the original R23 SRAM accessors. */
#ifndef S2B_WORLD_VALUES_H
#define S2B_WORLD_VALUES_H
#include <stdint.h>
#include "globdata.h"
#include "r_main.h"
static inline uint32_t S2B_Mix(uint32_t h,uint32_t v){
#if defined(SCD_M15)
return (((h<<5)|(h>>27))^v)+0x9e3779b9UL;
#else
return (h^v)*16777619UL;
#endif
}
static inline void S2B_SectorValues(uint16_t id,uint32_t v[5])
{
    const sector_t *s=&_g_sectors[id];
    v[0]=s->floorheight;v[1]=s->ceilingheight;
    v[2]=(int32_t)s->floorpic;v[3]=(int32_t)s->ceilingpic;v[4]=(int32_t)s->lightlevel;
}
static inline void S2B_SideValues(uint16_t id,uint32_t v[4])
{
    const side_t *s=&_g_sides[id];
    v[0]=(int32_t)R23_GET(s,textureoffset);v[1]=(int32_t)R23_GET(s,toptexture);
    v[2]=(int32_t)R23_GET(s,bottomtexture);v[3]=(int32_t)R23_GET(s,midtexture);
}
#endif

