/* R46 M2C/P2I: caller-owned packed 4bpp raster target, 76x44.
 * This is a testable software target, not _s_screen ownership or VDP.
 */
#ifndef R46_P4_RASTER_H
#define R46_P4_RASTER_H
#include <stdint.h>
enum {
    R46_P4_RASTER_W=76,
    R46_P4_RASTER_H=44,
    R46_P4_RASTER_PITCH=38,
    R46_P4_RASTER_BYTES=1672
};
#if defined(DOOM_R46_M2C)
/* clear only rows >= keep_rows, preserve top reserved rows; zero extra BSS.
 * The entire target must have capacity >=1672 or remain unchanged.
 * colors are palette indices 0..15, even pixel in high nibble. */
uint16_t R46_P4_ClearTarget(uint8_t *target,uint16_t capacity,
                            uint8_t color,uint16_t keep_rows);
uint16_t R46_P4_FillRow(uint8_t *target,uint16_t capacity,
    uint16_t y,uint16_t first,uint16_t last,uint8_t color);
uint16_t R46_P4_FillColumn(uint8_t *target,uint16_t capacity,
    uint16_t x,uint16_t first,uint16_t last,uint8_t color);
/* Return 0xFF for invalid arguments, otherwise 4bpp pixel index. */
uint8_t R46_P4_ReadSample(const uint8_t *target,uint16_t capacity,
                          uint16_t x,uint16_t y);
uint16_t R46_P4_RasterValidate(void);
#endif
#endif
