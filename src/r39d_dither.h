/* R39d: 8x8 wall/sprite/flat checkerboard vs solid runtime tile mappings. */
#ifndef R39D_DITHER_H
#define R39D_DITHER_H
#include <stdint.h>
#if defined(DOOM_R39D_DITHER_TOGGLE)
uint16_t R39D_DitherEnabled(void);
void R39D_SetDither(uint16_t enabled);
#endif
#endif
