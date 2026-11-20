#ifndef MAPDATA_H
#define MAPDATA_H
#ifdef SGDK_GCC
#include <types.h>   /* SGDK provides the intN_t names */
#else
#include <stdint.h>
#endif

#define NUM_BUCKETS 4

typedef struct {
    uint16_t v1, v2;
    uint8_t  front, back;          /* sector indices, back = 0xFF if one-sided */
    uint8_t  mid, upper, lower;    /* texture index, 0xFF none */
    uint8_t  flags;                /* 1 upper unpegged, 2 lower unpegged, 4 two-sided */
    int16_t  xoff, yoff;           /* texture offsets (seg offset + sidedef x offset) */
    uint16_t line;
    int16_t  len;                  /* seg length, map units */
} MapSeg;

typedef struct { uint16_t first; uint16_t count; uint16_t sector; } MapSub;

typedef struct {
    int16_t x, y, dx, dy;
    int16_t bbox[2][4];            /* [child][top, bottom, left, right] */
    uint16_t child[2];             /* 0x8000 = subsector */
} MapNode;

typedef struct {
    int16_t floor, ceil;
    uint8_t floorcol, ceilcol;     /* pair of MD palette indices (one byte = 2 pixels) */
    uint8_t bucket, sky;
} MapSector;

typedef struct { uint16_t v1, v2, flags; uint16_t front, back; } MapLine;

typedef struct {
    uint8_t wshift, hshift;        /* stored width (half of the original) and height, log2 */
    int16_t realh, realw;
    uint32_t off[NUM_BUCKETS];     /* offset of each light bucket in tex_blob */
} MapTex;

extern const uint16_t md_palette[16];
extern const uint8_t pal_rgb[16][3];
extern const int16_t map_verts[][2];
extern const MapSeg map_segs[];
extern const MapSub map_subs[];
extern const MapNode map_nodes[];
extern const MapSector map_sectors_init[];
extern const MapLine map_lines[];
extern const uint8_t tex_blob[];
extern const MapTex map_tex[];
extern const int16_t map_start[3];
extern const uint16_t map_counts[6];   /* verts, segs, subsectors, nodes, sectors, lines */
#endif
