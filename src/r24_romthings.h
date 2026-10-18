#ifndef R24_ROMTHINGS_H
#define R24_ROMTHINGS_H
#include "r_defs.h"
#if defined(DOOM_R24_EPISODE)
extern int16_t r24_start_map;
void R24_InitThings(int16_t map,int16_t lump);
int R24_IsRomThing(uint16_t index);
int R24_SpawnRomThing(uint16_t index,const mapthing_t *mt);
int R24_RemoveRomThing(mobj_t *thing);
boolean R24_BlockIterator(int16_t x,int16_t y,boolean (*func)(mobj_t*));
void R24_ProjectSector(sector_t *sec,int16_t light,void (*project)(mobj_t*,int16_t));
void M_R24OpenLevels(void);
void R24_ValidateThings(void);
#endif
#endif
