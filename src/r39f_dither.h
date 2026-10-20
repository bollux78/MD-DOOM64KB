/* R39f: compare real R35d 8x8 checkerboard, vertical 1-pixel stripes,
 * and original solid tiles at runtime without reloading the level. */
#ifndef R39F_DITHER_H
#define R39F_DITHER_H
#include <stdint.h>
#if defined(DOOM_R39F_DITHER3)
enum { R39F_SOLID = 0, R39F_CHECKER = 1, R39F_VERTICAL = 2 };
uint16_t R39F_DitherMode(void);
void R39F_SetDitherMode(uint16_t mode);
#endif
#endif
