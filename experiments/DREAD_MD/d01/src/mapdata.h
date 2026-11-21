#ifndef MAPDATA_H
#define MAPDATA_H
#ifdef SGDK_GCC
#include <types.h>   /* SGDK provides the intN_t names */
#else
#include <stdint.h>
#endif

#define NUM_BUCKETS 4
#define NO_MAP_SECTOR 0xFFFFu
#define EP_TEX_PAD 32                  /* episode builds: texels repeated after each column (instead of a full second copy) */

typedef struct {
    uint16_t v1, v2;
    uint16_t front, back;          /* NO_MAP_SECTOR for a missing side */
    uint8_t  mid, upper, lower;    /* texture index, 0xFF none */
    uint8_t  flags;                /* 1 upper unpegged, 2 lower unpegged, 4 two-sided */
    int16_t  xoff, yoff;           /* texture offsets (seg offset + sidedef x offset) */
#ifndef DREAD_EPISODE
    uint16_t line;
#endif
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
    uint8_t floorpal, ceilpal;     /* which of the view palettes (per 8x8 tile) */
} MapSector;

typedef struct { uint16_t v1, v2, flags; uint16_t front, back; uint16_t special, tag; } MapLine;
typedef struct { uint16_t sector; int16_t open_ceil; } MapDoor;

typedef struct {
    uint8_t wshift, hshift;        /* stored width (half of the original) and height, log2 */
    int16_t realh, realw;
    uint32_t off[NUM_BUCKETS];     /* offset of each light bucket in tex_blob */
    uint8_t pal[NUM_BUCKETS];      /* palette of each light bucket */
} MapTex;

extern const uint16_t md_palette[][16];
extern const uint8_t pal_rgb_all[][16][3];
extern const uint16_t num_palettes;
extern const uint8_t pal_remap[][256];   /* [A*NPAL+B][byte ^ 0x80] */
extern const int16_t map_verts[][2];
extern const MapSeg map_segs[];
extern const MapSub map_subs[];
extern const MapNode map_nodes[];
extern const MapSector map_sectors_init[];
extern const MapLine map_lines[];
extern const MapDoor map_doors[];
extern const uint16_t map_ndoors;
extern const int16_t map_sector_tag[];
extern const uint8_t tex_blob[];
extern const uint16_t tex_blob_w[];
extern const MapTex map_tex[];
extern const int16_t map_start[3];
extern const uint16_t map_counts[6];
typedef struct { int16_t w2, h, leftoff, topoff; uint32_t off[NUM_BUCKETS]; } MapSprite;   /* w2 = half width */
typedef struct { int16_t x, y; uint16_t sprite, sub, flags; } MapThing;   /* flags 1 = monster; sorted by sub */
extern const uint8_t spr_blob[];
extern const MapSprite map_sprites[];
extern const MapThing map_things[];
extern const uint16_t map_nthings;
extern const uint16_t map_sub_things[];   /* things of subsector s: [map_sub_things[s], map_sub_things[s+1]) */
extern const int16_t map_bm[4];          /* collision grid: x0, y0, width, height (128-unit cells) */
extern const uint16_t map_bm_off[], map_bm_list[];
extern const uint16_t map_mframes[];   /* monster sprite per (kind, frame letter, rotation 1-5): [(k*16+f)*5+r], 0xFFFF none */
extern const uint16_t map_fx[8];       /* imp ball A B, explosion C D E, baron ball A B, caco ball */
extern const uint8_t map_reject[];     /* REJECT: bit (s1*nsec+s2) set = s1 cannot see s2 */
extern const uint16_t map_secadj_off[], map_secadj[];   /* sound: sector neighbours through two-sided lines */
#define THING_MONSTER 1
#define THING_AMBUSH 2
#define THING_DIR(f) (((f) >> 2) & 7)
#define THING_KIND(f) (((f) >> 8) & 15)   /* verts, segs, subsectors, nodes, sectors, lines */

#ifdef DREAD_EPISODE
typedef struct {
    const int16_t (*map_verts)[2];
    const MapSeg *map_segs;
    const MapSub *map_subs;
    const MapNode *map_nodes;
    const MapSector *map_sectors_init;
    const MapLine *map_lines;
    const MapDoor *map_doors;
    uint16_t map_ndoors;
    const int16_t *map_sector_tag;
    const MapTex *map_tex;
    const int16_t *map_start;
    const uint16_t *map_counts;
    const MapSprite *map_sprites;
    const MapThing *map_things;
    uint16_t map_nthings;
    const uint16_t *map_sub_things;
    const int16_t *map_bm;
    const uint16_t *map_bm_off;
    const uint16_t *map_bm_list;
    const uint16_t *map_mframes;
    const uint16_t *map_fx;
    const uint8_t *map_reject;
    const uint16_t *map_secadj_off;
    const uint16_t *map_secadj;
    const uint32_t *pvs_offsets;
    uint16_t pvs_nbytes, pvs_sbytes;
} DreadMap;
extern const DreadMap *dread_map;
extern const DreadMap episode_maps[];
extern const uint16_t episode_map_count, episode_map_numbers[];
extern const uint8_t episode_pvs[];
extern const uint8_t *const tex_columns[];
#ifndef DREAD_EPISODE_DATA
#define map_verts (dread_map->map_verts)
#define map_segs (dread_map->map_segs)
#define map_subs (dread_map->map_subs)
#define map_nodes (dread_map->map_nodes)
#define map_sectors_init (dread_map->map_sectors_init)
#define map_lines (dread_map->map_lines)
#define map_doors (dread_map->map_doors)
#define map_ndoors (dread_map->map_ndoors)
#define map_sector_tag (dread_map->map_sector_tag)
#define map_tex (dread_map->map_tex)
#define map_start (dread_map->map_start)
#define map_counts (dread_map->map_counts)
#define map_sprites (dread_map->map_sprites)
#define map_things (dread_map->map_things)
#define map_nthings (dread_map->map_nthings)
#define map_sub_things (dread_map->map_sub_things)
#define map_bm (dread_map->map_bm)
#define map_bm_off (dread_map->map_bm_off)
#define map_bm_list (dread_map->map_bm_list)
#define map_mframes (dread_map->map_mframes)
#define map_fx (dread_map->map_fx)
#define map_reject (dread_map->map_reject)
#define map_secadj_off (dread_map->map_secadj_off)
#define map_secadj (dread_map->map_secadj)
#endif
#endif
#endif
