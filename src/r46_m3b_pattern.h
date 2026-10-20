/* R46 M3B: diagnostic packed-4bpp pattern in a caller-owned 1672B target.
 * All pixels in display rows 2..43 yield dynamic tiles (no solid indices).
 */
#ifndef R46_M3B_PATTERN_HEADER_H
#define R46_M3B_PATTERN_HEADER_H
#include <stdint.h>
#if defined(DOOM_R46_M2C)
uint16_t R46_M3B_MakePattern(uint8_t *pixels,uint16_t capacity);
uint16_t R46_M3B_PatternValidate(void);
#endif
#endif
