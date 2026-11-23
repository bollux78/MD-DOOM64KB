/* Host harness: render views of the converted map to PPM files (2 screen px per column).
 * usage: host OUT_PREFIX [x y angle_deg]...   (no args after prefix: start position, 8 angles) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "../src/render.h"
static uint8_t fb[FB_MAX];
static void save(const char *fn)
{
    /* as on screen: 320 pixels wide, rows doubled in the row-duplicated variant */
    static uint16_t nt[18 * 40];
    R_BuildNametable(nt, 0);
    const int RD = COLB == 1 ? 2 : 1;
    FILE *f = fopen(fn, "wb");
    fprintf(f, "P6 %d %d 255\n", FB_TCOLS * 8, VIEW_H * RD);
    for (int y = 0; y < VIEW_H * RD; y++)
        for (int x = 0; x < FB_TCOLS * 8; x++) {
            const int r = y / RD, bx = x >> 1;
            const uint8_t b = fb[(bx >> 2) * VIEW_H * 4 + r * 4 + (bx & 3)];
            const int pl = nt[(r >> 3) * FB_TCOLS + (bx >> 2)] >> 13;
            fwrite(pal_rgb_all[pl][(x & 1) ? (b & 15) : (b >> 4)], 1, 3, f);
        }
    fclose(f);
}
static void shot(const char *pre, int i, int x, int y, int deg)
{
    View v; v.x = (int32_t)x << 16; v.y = (int32_t)y << 16; v.angle = (uint16_t)(deg * 65536 / 360);
    v.z = map_sectors[map_subs[R_PointInSub(x, y)].sector].floor + 41;
    memset(fb, 0xEE, sizeof fb);   /* colour 14: anything not painted shows up */
    R_RenderView(&v, fb);
    char fn[256]; snprintf(fn, sizeof fn, "%s%02d.ppm", pre, i); save(fn);
    printf("%s x=%d y=%d a=%d segs=%u nodes=%u subs=%u closed=%u\n", fn, x, y, deg,
           rstats.segs_drawn, rstats.nodes_visited, rstats.subs_visited, rstats.cols_closed);
}
extern int r_pvs_off;
static uint8_t fb2[FB_MAX];
static void sweep(int n)
{
    srand(7); long bad = 0; int badviews = 0;
    for (int i = 0; i < n; i++) {
        const int s = rand() % map_counts[2];
        const MapSub *ss = &map_subs[s];
        double cx = 0, cy = 0;
        for (int k = 0; k < ss->count; k++) { cx += map_verts[map_segs[ss->first + k].v1][0]; cy += map_verts[map_segs[ss->first + k].v1][1]; }
        cx /= ss->count; cy /= ss->count;
        const int k = rand() % ss->count; const int v = map_segs[ss->first + k].v1;
        const double t = (rand() % 100) / 100.0;
        View vw; vw.x = (int32_t)((cx + (map_verts[v][0] - cx) * t * 0.9) * 65536); vw.y = (int32_t)((cy + (map_verts[v][1] - cy) * t * 0.9) * 65536);
        vw.angle = (uint16_t)rand();
        vw.z = map_sectors[map_subs[R_PointInSub(vw.x >> 16, vw.y >> 16)].sector].floor + 41;
        r_pvs_off = 1; R_RenderView(&vw, fb2);
        r_pvs_off = 0; R_RenderView(&vw, fb);
        long d = 0; for (int b = 0; b < FB_BYTES; b++) d += fb[b] != fb2[b];
        if (d) { bad += d; badviews++; if (badviews <= 5) printf("diff %ld px at %d,%d a=%u\n", d, vw.x >> 16, vw.y >> 16, vw.angle); }
    }
    printf("sweep: %d views, %d with differences, %ld byte diffs\n", n, badviews, bad);
}
/* cmp N [POSFILE [DUMPFILE]]: N views for A/B checks between converted variants of the same map.
 * Positions are chosen inside the map (right of every seg of their subsector, in the unmodified map) and
 * saved to POSFILE; give the same POSFILE to the other variants so every build renders the SAME views.
 * DUMPFILE receives every framebuffer (FB_BYTES each) for a pixel-level comparison. One line per view: index, framebuffer hash, segs drawn, BSP nodes, subsectors, column visits, x y z angle. */
static int inside_map(int x, int y)
{
    const MapSub *ss = &map_subs[R_PointInSub(x, y)];
    for (int k = 0; k < ss->count; k++) {
        const MapSeg *sg = &map_segs[ss->first + k];
        const long dx = map_verts[sg->v2][0] - map_verts[sg->v1][0], dy = map_verts[sg->v2][1] - map_verts[sg->v1][1];
        if (dx * (y - map_verts[sg->v1][1]) - dy * (x - map_verts[sg->v1][0]) > 0) return 0;
    }
    return ss->count > 0;
}
static void cmp(int n, const char *posfile, const char *dumpfile)
{
    FILE *dump = dumpfile ? fopen(dumpfile, "wb") : NULL;
    int px[4096], py[4096], pa[4096];
    FILE *pf = posfile ? fopen(posfile, "r") : NULL;
    if (n > 4096) n = 4096;
    int have = 0;
    if (pf) { while (have < n && fscanf(pf, "%d %d %d", &px[have], &py[have], &pa[have]) == 3) have++; fclose(pf); }
    if (have < n) {
        int minx = 32767, miny = 32767, maxx = -32768, maxy = -32768;
        for (int i = 0; i < map_counts[0]; i++) {
            if (map_verts[i][0] < minx) minx = map_verts[i][0];
            if (map_verts[i][0] > maxx) maxx = map_verts[i][0];
            if (map_verts[i][1] < miny) miny = map_verts[i][1];
            if (map_verts[i][1] > maxy) maxy = map_verts[i][1];
        }
        srand(11);
        for (long guard = 0; have < n && guard < 4000000; guard++) {
            const int x = minx + rand() % (maxx - minx + 1), y = miny + rand() % (maxy - miny + 1);
            if (!inside_map(x, y)) continue;
            px[have] = x; py[have] = y; pa[have] = rand() & 0xFFFF; have++;
        }
        n = have;
        if (posfile) { pf = fopen(posfile, "w"); for (int i = 0; i < n; i++) fprintf(pf, "%d %d %d\n", px[i], py[i], pa[i]); fclose(pf); }
    }
    unsigned long tsegs = 0, tnodes = 0, tcols = 0, tsubs = 0;
    for (int i = 0; i < n; i++) {
        View v; v.x = (int32_t)px[i] << 16; v.y = (int32_t)py[i] << 16; v.angle = (uint16_t)pa[i];
        v.z = map_sectors[map_subs[R_PointInSub(px[i], py[i])].sector].floor + 41;
        memset(fb, 0xEE, sizeof fb);
        R_RenderView(&v, fb);
        if (dump) fwrite(fb, 1, FB_BYTES, dump);
        uint32_t h = 2166136261u;
        for (int b = 0; b < FB_BYTES; b++) h = (h ^ fb[b]) * 16777619u;
        printf("%d %08x %u %u %u %u %d %d %d %u\n", i, h, rstats.segs_drawn, rstats.nodes_visited, rstats.subs_visited, rstats.col_visits, px[i], py[i], (int)v.z, (unsigned)v.angle);
        tsegs += rstats.segs_drawn; tnodes += rstats.nodes_visited; tsubs += rstats.subs_visited; tcols += rstats.col_visits;
    }
    printf("TOTAL views=%d segs=%lu nodes=%lu subs=%lu colvisits=%lu fbbytes=%d\n", n, tsegs, tnodes, tsubs, tcols, (int)FB_BYTES);
    if (dump) fclose(dump);
}
int main(int argc, char **argv)
{
    R_Init();
    if (argc > 2 && !strcmp(argv[2], "sweep")) { sweep(atoi(argv[3])); return 0; }
    if (argc > 3 && !strcmp(argv[2], "cmp")) { cmp(atoi(argv[3]), argc > 4 ? argv[4] : NULL, argc > 5 ? argv[5] : NULL); return 0; }
    if (argc > 3 && !strcmp(argv[2], "things")) {   /* things N: views of the first N things from 4 sides */
        int n = atoi(argv[3]), k = 0;
        static const int dx[4] = {96, 0, -96, 0}, dy[4] = {0, 96, 0, -96}, ang[4] = {180, 270, 0, 90};
        const int mons = argc > 4 && argv[4][0] == 'm';
        for (int i = 0, c = 0; i < map_nthings && c < n; i++) {
            if (mons && !(map_things[i].flags & 1)) continue;
            c++;
            for (int d = 0; d < 4; d++, k++) shot(argv[1], k, map_things[i].x + dx[d], map_things[i].y + dy[d], ang[d]);
        }
        return 0;
    }
    if (argc > 6 && !strcmp(argv[2], "raw")) {   /* raw X16 Y16 Z ANGLE16: exact view (from a ROM RAM dump) */
        View v; v.x = atol(argv[3]); v.y = atol(argv[4]); v.z = (int16_t)atoi(argv[5]); v.angle = (uint16_t)atol(argv[6]);
        memset(fb, 0xEE, sizeof fb); R_RenderView(&v, fb);
        char fn[256]; snprintf(fn, sizeof fn, "%sraw.ppm", argv[1]); save(fn); return 0;
    }
    if (argc <= 2) {
        for (int i = 0; i < 8; i++) shot(argv[1], i, map_start[0], map_start[1], map_start[2] + i * 45);
    } else {
        for (int i = 2, k = 0; i + 2 < argc; i += 3, k++) shot(argv[1], k, atoi(argv[i]), atoi(argv[i + 1]), atoi(argv[i + 2]));
    }
    /* timing */
    View v; v.x = (int32_t)map_start[0] << 16; v.y = (int32_t)map_start[1] << 16; v.z = 41; v.angle = 0;
    clock_t t0 = clock(); for (int i = 0; i < 2000; i++) { v.angle += 300; R_RenderView(&v, fb); }
    printf("host: %.3f ms/frame\n", (double)(clock() - t0) * 1000.0 / CLOCKS_PER_SEC / 2000);
    return 0;
}
