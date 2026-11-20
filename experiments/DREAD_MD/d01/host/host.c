/* Host harness: render views of the converted map to PPM files (2 screen px per column).
 * usage: host OUT_PREFIX [x y angle_deg]...   (no args after prefix: start position, 8 angles) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "../src/render.h"
static uint8_t fb[FB_BYTES];
static void save(const char *fn)
{
    FILE *f = fopen(fn, "wb");
    fprintf(f, "P6 %d %d 255\n", VIEW_W * 2, VIEW_H);
    for (int y = 0; y < VIEW_H; y++)
        for (int x = 0; x < VIEW_W; x++) {
            const uint8_t b = FB_COL(fb, x)[y * 4];
            for (int k = 0; k < 2; k++) fwrite(pal_rgb[k ? (b & 15) : (b >> 4)], 1, 3, f);
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
int main(int argc, char **argv)
{
    R_Init();
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
