/* DREAD-MD PVS generator (host): for every subsector, render from sample points inside it in
 * 16 directions with the real renderer and record which subsectors drew anything. The union,
 * dilated by the neighbouring subsectors, is that subsector's potentially visible set.
 * Output: pvs.c with one node bitset and one subsector bitset per subsector.
 * build: gcc -O2 -DPVS_GEN -DMAXV=4096 -Isrc tools/pvsgen.c src/render.c mapdata.c */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "render.h"
extern uint8_t pvs_seen[];
static uint8_t fb[FB_BYTES];

static int nsub, nnode;
static uint8_t *vis;          /* nsub x nsub */

static void mark_nodes(uint16_t n, const uint8_t *subs, uint8_t *nodes, int *any)
{
    if (n & 0x8000) { *any = subs[n & 0x7FFF]; return; }
    int a = 0, b = 0;
    mark_nodes(map_nodes[n].child[0], subs, nodes, &a);
    mark_nodes(map_nodes[n].child[1], subs, nodes, &b);
    *any = a | b;
    if (*any) nodes[n] = 1;
}

int main(int argc, char **argv)
{
    nsub = map_counts[2]; nnode = map_counts[3];
    R_Init();
    /* doors open: everything behind a door must be in the visible sets */
    for (int d = 0; d < map_ndoors; d++) map_sectors[map_doors[d].sector].ceil = map_doors[d].open_ceil;
    vis = calloc((size_t)nsub * nsub, 1);
    for (int i = 0; i < nsub; i++) {
        const MapSub *ss = &map_subs[i];
        double cx = 0, cy = 0; int nv = 0;
        for (int k = 0; k < ss->count; k++) {
            const MapSeg *sg = &map_segs[ss->first + k];
            cx += map_verts[sg->v1][0]; cy += map_verts[sg->v1][1]; nv++;
        }
        cx /= nv; cy /= nv;
        double px[200], py[200]; int np = 0;
        px[np] = cx; py[np] = cy; np++;
        for (int k = 0; k < ss->count && np < 60; k++) {
            const MapSeg *sg = &map_segs[ss->first + k];
            for (int e = 0; e < 2 && np < 60; e++) {
                const int v = e ? sg->v2 : sg->v1;
                px[np] = map_verts[v][0] + (cx - map_verts[v][0]) * 0.03;
                py[np] = map_verts[v][1] + (cy - map_verts[v][1]) * 0.03; np++;
            }
            /* midpoint of the seg, pulled in */
            const double mx = (map_verts[sg->v1][0] + map_verts[sg->v2][0]) / 2.0, my = (map_verts[sg->v1][1] + map_verts[sg->v2][1]) / 2.0;
            px[np] = mx + (cx - mx) * 0.03; py[np] = my + (cy - my) * 0.03; np++;
        }
        /* plus a grid over the subsector (points that locate inside it) */
        {
            double x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
            for (int k = 0; k < ss->count; k++) {
                const MapSeg *sg = &map_segs[ss->first + k];
                const double vx = map_verts[sg->v1][0], vy = map_verts[sg->v1][1];
                if (vx < x0) x0 = vx; if (vx > x1) x1 = vx; if (vy < y0) y0 = vy; if (vy > y1) y1 = vy;
            }
            double step = 12;
            while ((x1 - x0) / step * (y1 - y0) / step > 120) step *= 1.5;
            for (double gx = x0 + step / 2; gx < x1 && np < 190; gx += step)
                for (double gy = y0 + step / 2; gy < y1 && np < 190; gy += step)
                    if (R_PointInSub((int16_t)gx, (int16_t)gy) == i) { px[np] = gx; py[np] = gy; np++; }
        }
        const MapSector *sec = &map_sectors[ss->sector];
        for (int p = 0; p < np; p++)
            for (int a = 0; a < 16; a++)
                for (int h = 0; h < 2; h++) {
                    View v;
                    v.x = (int32_t)(px[p] * 65536.0); v.y = (int32_t)(py[p] * 65536.0);
                    v.z = sec->floor + (h ? 41 : 20);
                    if (v.z > sec->ceil - 4) v.z = sec->ceil - 4;
                    v.angle = (uint16_t)(a * 4096 + 2048 * h);
                    memset(pvs_seen, 0, nsub);
                    R_RenderView(&v, fb);
                    for (int s = 0; s < nsub; s++) if (pvs_seen[s]) vis[(size_t)i * nsub + s] = 1;
                }
        vis[(size_t)i * nsub + i] = 1;
    }
    /* dilate: a subsector also sees what its neighbours (sharing a vertex) see */
    uint8_t *nb = calloc((size_t)nsub * nsub, 1);
    {
        int *subofv = malloc(sizeof(int) * map_counts[0] * 8); int *cnt = calloc(map_counts[0], sizeof(int));
        for (int i = 0; i < nsub; i++)
            for (int k = 0; k < map_subs[i].count; k++) {
                const MapSeg *sg = &map_segs[map_subs[i].first + k];
                for (int e = 0; e < 2; e++) { const int v = e ? sg->v2 : sg->v1; if (cnt[v] < 8) subofv[v * 8 + cnt[v]++] = i; }
            }
        for (int v = 0; v < map_counts[0]; v++)
            for (int a = 0; a < cnt[v]; a++) for (int b = 0; b < cnt[v]; b++) nb[(size_t)subofv[v * 8 + a] * nsub + subofv[v * 8 + b]] = 1;
    }
    /* two rings: neighbours of neighbours */
    {
        uint8_t *nb2 = calloc((size_t)nsub * nsub, 1);
        for (int i = 0; i < nsub; i++) for (int j = 0; j < nsub; j++) if (nb[(size_t)i * nsub + j])
            for (int k = 0; k < nsub; k++) nb2[(size_t)i * nsub + k] |= nb[(size_t)j * nsub + k];
        free(nb); nb = nb2;
    }
    uint8_t *vis2 = calloc((size_t)nsub * nsub, 1);
    for (int i = 0; i < nsub; i++)
        for (int j = 0; j < nsub; j++) if (nb[(size_t)i * nsub + j])
            for (int s = 0; s < nsub; s++) vis2[(size_t)i * nsub + s] |= vis[(size_t)j * nsub + s];
    const int sbytes = (nsub + 7) / 8, nbytes = (nnode + 7) / 8;
    FILE *f = fopen(argv[1], "w");
    fprintf(f, "/* generated by pvsgen -- potentially visible sets */\n#include \"mapdata.h\"\n");
    fprintf(f, "const uint16_t pvs_nbytes = %d, pvs_sbytes = %d;\n", nbytes, sbytes);
    long tot = 0, tot1 = 0;
    fprintf(f, "const uint8_t pvs_subs[%d] = {", nsub * sbytes);
    for (int i = 0; i < nsub; i++) for (int b = 0; b < sbytes; b++) {
        int v = 0; for (int k = 0; k < 8; k++) { const int s = b * 8 + k; if (s < nsub && vis2[(size_t)i * nsub + s]) { v |= 1 << k; tot++; } if (s < nsub && vis[(size_t)i * nsub + s]) tot1++; }
        fprintf(f, "%d,", v);
    }
    fprintf(f, "};\nconst uint8_t pvs_nodes[%d] = {", nsub * nbytes);
    uint8_t *nodes = malloc(nnode);
    for (int i = 0; i < nsub; i++) {
        memset(nodes, 0, nnode); int any;
        mark_nodes(nnode - 1, vis2 + (size_t)i * nsub, nodes, &any);
        for (int b = 0; b < nbytes; b++) { int v = 0; for (int k = 0; k < 8; k++) if (b * 8 + k < nnode && nodes[b * 8 + k]) v |= 1 << k; fprintf(f, "%d,", v); }
    }
    fprintf(f, "};\n");
    fclose(f);
    printf("pvs: %d subsectors, avg visible %.1f (sampled %.1f), %d bytes\n", nsub, (double)tot / nsub, (double)tot1 / nsub, nsub * (sbytes + nbytes));
    return 0;
}
