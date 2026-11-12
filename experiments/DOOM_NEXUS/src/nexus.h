#ifndef NEXUS_H
#define NEXUS_H

#include <stdint.h>

#ifdef NX_2X2
enum { NX_WIDTH = 80, NX_HEIGHT = 60, NX_SCALE = 2 };
#else
enum { NX_WIDTH = 128, NX_HEIGHT = 96, NX_SCALE = 1 };
#endif
enum {
    NX_VIEW_WIDTH = NX_WIDTH * NX_SCALE,
    NX_VIEW_HEIGHT = NX_HEIGHT * NX_SCALE,
    NX_TILE_BYTES = NX_VIEW_WIDTH * NX_VIEW_HEIGHT / 2
};
enum { NX_LINEAR, NX_TILES };

typedef struct { int16_t x, y; } NxVertex;
typedef struct { int16_t floor, ceiling; } NxSector;
typedef struct { uint16_t a, b, front, back; } NxSeg;
typedef struct { uint16_t first, count; } NxLeaf;
typedef struct { int16_t top, bottom, left, right; } NxBounds;
typedef struct { int16_t x, y, dx, dy; uint16_t child[2]; NxBounds bounds[2]; } NxNode;
typedef struct { int16_t x, y, z, cosine, sine; } NxCamera;

typedef struct {
    const NxVertex *vertices;
    const NxSector *sectors;
    const NxSeg *segs;
    const NxLeaf *leaves;
    const NxNode *nodes;
    uint16_t root;
} NxMap;

void nx_camera_floor(const NxMap *map, NxCamera *camera);
void nx_render(const NxMap *map, const NxCamera *camera, uint8_t *pixels, int layout);
void nx_pack(const uint8_t *linear, uint8_t *tiles);

#endif
