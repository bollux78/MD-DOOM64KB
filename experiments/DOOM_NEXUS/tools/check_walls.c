#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nexus.h"

extern const NxMap nexus_map;
extern const NxCamera nexus_cameras[];
extern const unsigned int nexus_camera_count;

int main(void)
{
    _Alignas(4) uint8_t pixels[NX_WIDTH * NX_HEIGHT];
    uint8_t flat[NX_WIDTH * NX_HEIGHT];
    uint8_t perspective[NX_WIDTH * NX_HEIGHT];
    unsigned textured = 0, approximated = 0;
    for (unsigned i = 0; i < nexus_camera_count; ++i) {
        nx_render_walls(&nexus_map, &nexus_cameras[i], flat, NX_FLAT);
        for (int mode = 0; mode < NX_MODE_COUNT; ++mode) {
            memset(pixels, 0xff, sizeof pixels);
            nx_render_walls(&nexus_map, &nexus_cameras[i], pixels, mode);
            if (mode == NX_PERSPECTIVE)
                memcpy(perspective, pixels, sizeof pixels);
            for (unsigned y = 0; y < NX_HEIGHT; ++y) {
                for (unsigned x = 0; x < NX_WIDTH; ++x) {
                    unsigned index = nx_linear_index(x, y);
                    unsigned p = pixels[index];
                    if (p == 0 || p == 7 || p > 15 ||
                        (flat[index] <= 2 && flat[index] != p)) {
                        fprintf(stderr, "Invalid pixel at pose %u, mode %d, %u,%u\n",
                                i, mode, x, y);
                        return EXIT_FAILURE;
                    }
                    if (mode == NX_PERSPECTIVE)
                        textured += p != flat[index];
                    if (mode == NX_STRIP)
                        approximated += p != perspective[index];
                    if (putchar(p) == EOF)
                        return EXIT_FAILURE;
                }
            }
        }
    }
    if (!textured || !approximated) {
        fputs("Texture modes did not change the rendered walls\n", stderr);
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
