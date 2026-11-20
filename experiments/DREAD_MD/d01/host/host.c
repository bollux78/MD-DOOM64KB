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
int main(int argc, char **argv)
{
    R_Init();
    if (argc > 2 && !strcmp(argv[2], "sweep")) { sweep(atoi(argv[3])); return 0; }
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
