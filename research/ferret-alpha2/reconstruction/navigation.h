#ifndef NAVIGATION_H
#define NAVIGATION_H
#include <stdint.h>
typedef struct {int16_t x0,y0,x1,y1,h[4],u0,u1;uint8_t color0,color1,variant,back_variant;uint32_t tex0,tex1;} Wall;
typedef struct {int16_t x,y,z,si,co,sky;} Camera;
typedef struct {int16_t nx,ny;int32_t distance;int16_t child[2];} MapNode;
extern const Wall scene_walls[];
extern const uint16_t scene_wall_count,map_node_count,map_cell_count;
extern const MapNode map_nodes[];
extern const uint16_t map_cell_walls[];
extern const uint32_t map_cell_offsets[];
extern const int16_t map_cell_floor[],map_sine[256];
extern const Camera map_spawn;
extern const uint8_t texture_blob[],sky_columns[128][72];
extern const int16_t sample_offsets[2048][72];
extern const int16_t collision_origin_x,collision_origin_y;
extern const uint16_t collision_width,collision_height;
extern const uint32_t collision_offsets[];
extern const uint16_t collision_walls[];
uint16_t map_find_cell(int16_t x,int16_t y);
void render_view(uint8_t*,const Camera*,uint16_t);
void navigation_reset(void);
void navigation_update(uint16_t buttons,uint16_t ticks);
extern Camera navigation_camera;
extern uint16_t navigation_cell,navigation_angle;
#endif
