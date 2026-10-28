#ifndef R81_SAVE_IO_H
#define R81_SAVE_IO_H
#include <stdint.h>
#include <stddef.h>
#include "r81_save.h"
#define R81_MEASURE 0
#define R81_WRITE 1
#define R81_LOAD 2
#define R81_VALIDATE 3
#define R81_MAX_OBJECTS 512u
typedef struct {
    uint16_t pos,limit,crc,object_count,object_index,player_id;
    uint16_t lines,sides,sectors,statics;
    uint8_t mode,error,zero_run,map,skill;
    mobj_t **objects;
    const line_t *maplines;
    const mapsidedef_t *mapsides;
    const mapsector_t *mapsectors;
} r81_io_t;
typedef struct {uint16_t offset;uint8_t size,count;} r81_field_t;
#define R81_F(t,m) {offsetof(t,m),sizeof(((t*)0)->m),1}
#define R81_A(t,m,n) {offsetof(t,m),sizeof(((t*)0)->m[0]),n}
uint8_t R81_SramRead(uint16_t logical);
void R81_SramWrite(uint16_t logical,uint8_t value);
uint32_t R81_U(r81_io_t *io,uint32_t value);
int32_t R81_N(r81_io_t *io,int32_t value);
void R81_Fields(r81_io_t *io,void *object,const r81_field_t *fields,uint16_t count);
int32_t R81_GetField(const void *object,const r81_field_t *field);
uint16_t R81_ObjectId(r81_io_t *io,const mobj_t *object);
uint16_t R81_SectorId(r81_io_t *io,const sector_t *sector);
void R81_RandomArchive(r81_io_t *io);
void R81_RomThingsArchive(r81_io_t *io);
uint8_t R81_MobjFunction(const thinker_t *th);
void R81_SetMobjFunction(mobj_t *mo,uint8_t kind);
mobj_t *R81_AllocMobj(void);
int R81_PendingThing(const thinker_t *th);
int R81_PendingSpecial(const thinker_t *th);
int R81_IsFloor(const thinker_t *th);
int R81_IsPlat(const thinker_t *th);
int R81_LightKind(const thinker_t *th);
void R81_FloorArchive(r81_io_t *io,thinker_t *th);
void R81_DoorArchive(r81_io_t *io,thinker_t *th);
void R81_PlatArchive(r81_io_t *io,thinker_t *th);
void R81_LightArchive(r81_io_t *io,thinker_t *th,uint8_t kind);
void R81_ResetMapLinks(void);
#endif
