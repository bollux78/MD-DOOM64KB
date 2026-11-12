#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nexus.h"

extern const NxMap nexus_map;
extern const NxCamera nexus_cameras[];
extern const unsigned int nexus_camera_count;

int main(void)
{
    uint8_t linear[NX_WIDTH * NX_HEIGHT];
    uint8_t expected[NX_TILE_BYTES];
    uint8_t direct[NX_TILE_BYTES];

    for (unsigned i = 0; i < nexus_camera_count; ++i) {
        memset(linear, 0xff, sizeof linear);
        memset(direct, 0xa5, sizeof direct);
        nx_render(&nexus_map, &nexus_cameras[i], linear, NX_LINEAR);
        nx_render(&nexus_map, &nexus_cameras[i], direct, NX_TILES);
        nx_pack(linear, expected);
        if (memcmp(expected, direct, sizeof direct)) {
            fprintf(stderr, "A/B tile mismatch on pose %u\n", i);
            return EXIT_FAILURE;
        }
        for (unsigned p = 0; p < sizeof linear; ++p) {
            if (linear[p] < 1 || linear[p] > 7) {
                fprintf(stderr, "Unwritten pixel on pose %u\n", i);
                return EXIT_FAILURE;
            }
        }
        for (unsigned y = 0; y < NX_HEIGHT; ++y)
            for (unsigned x = 0; x < NX_WIDTH; ++x)
                if (putchar(linear[nx_linear_index(x, y)]) == EOF)
                    return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
