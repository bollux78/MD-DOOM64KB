#ifndef NEXUS_H
#define NEXUS_H

#include <stdint.h>

enum { NX_WIDTH = 128, NX_HEIGHT = 96, NX_TILE_BYTES = 6144 };
enum { NX_LINEAR, NX_TILES };

typedef struct { int16_t x, y; } NxVertex;
typedef struct { int16_t floor, ceiling; } NxSector;
typedef struct { uint16_t a, b, front, back; } NxSeg;
typedef struct { uint16_t first, count; } NxLeaf;
typedef struct { int16_t x, y, dx, dy; uint16_t child[2]; } NxNode;
typedef struct { int16_t x, y, z, cosine, sine; } NxCamera;

typedef struct {
    const NxVertex *vertices;
    const NxSector *sectors;
    const NxSeg *segs;
    const NxLeaf *leaves;
    const NxNode *nodes;
    uint16_t root;
} NxMap;

void nx_render(const NxMap *map, const NxCamera *camera, uint8_t *pixels, int layout);
void nx_pack(const uint8_t *linear, uint8_t *tiles);

#endif
