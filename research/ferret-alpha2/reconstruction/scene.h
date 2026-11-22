#ifndef SCENE_H
#define SCENE_H
#include <stdint.h>
typedef struct { int16_t x0,y0,x1,y1,h[4],u0,u1; uint8_t color0,color1,variant,pad; uint32_t tex0,tex1; } Wall;
typedef struct { int16_t x,y,z,si,co,sky; } Camera;
extern const Wall scene_walls[];
extern const uint16_t scene_wall_count;
extern const Camera scene_cameras[16];
extern const uint8_t texture_blob[],sky_columns[128][72];
extern const int16_t sample_offsets[2048][72];
void render_scene(uint8_t *pixels,uint16_t camera);
#endif
