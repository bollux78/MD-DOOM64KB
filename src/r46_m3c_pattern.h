/* R46 M3C: deterministic changing packed-4bpp diagnostic frames. */
#ifndef R46_M3C_PATTERN_HEADER_H
#define R46_M3C_PATTERN_HEADER_H
#include <stdint.h>
#if defined(DOOM_R46_M2C)
uint16_t R46_M3C_MakePattern(uint8_t *pixels,uint16_t capacity,
                            uint16_t phase);
uint16_t R46_M3C_PatternValidate(void);
#endif
#endif
