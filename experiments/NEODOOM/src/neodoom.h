#ifndef NEODOOM_H
#define NEODOOM_H
#include <stdint.h>
enum {ND_W=72,ND_H=40,ND_FOCAL=36,ND_BYTES=72*40,ND_TILES=36*20,ND_TILE_BYTES=ND_TILES*32};
typedef struct {int16_t ax,ay,bx,by,nx,ny;int32_t plane;uint16_t next,mid,upper,lower;int16_t xoff,yoff;uint16_t flags;int16_t ux,uy;int32_t origin;} NdEdge;
typedef struct {uint16_t first,count;int16_t floor,ceiling;uint16_t sector;} NdRoom;
typedef struct {int16_t x,y;uint16_t angle;} NdPose;
typedef struct {int16_t x,y,z;uint16_t angle,room;} NdCamera;
typedef struct {uint32_t edges,portals,rays,overflow;} NdStats;
extern const NdEdge nd_edges[];
extern const NdRoom nd_rooms[];
extern const uint16_t nd_room_count,nd_pose_count,nd_palette[16];
extern const NdPose nd_poses[];
extern const int16_t nd_sines[256];
extern const uint8_t *const nd_textures[];
extern NdStats nd_stats;
int16_t nd_locate(int16_t x,int16_t y,int16_t hint);
void nd_render(const NdCamera *cam,uint8_t *pixels);
void nd_pack(const uint8_t *pixels,uint32_t *tiles);
uint16_t nd_pack_mixed(const uint8_t *,uint32_t *,uint16_t *,uint16_t,uint16_t);
#endif
