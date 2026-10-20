/* R46 M1B: native pixel4 VRAM/packing helpers co-linked with 8x8.
 * NO VDP register writes and NO additional global framebuffer/map.
 * Caller can only read the shared 4bpp framebuffer once a future
 * ownership protocol has safely retired all R20 DMA/ISR users.
 */
#ifndef R46_PIXEL4_VRAM_H
#define R46_PIXEL4_VRAM_H
#include <stdint.h>

enum {
    R46_P4_SOLID_TILES = 16,
    R46_P4_BANK_TILES = 836,
    R46_P4_COLUMNS = 38,
    R46_P4_ROWS = 21,
    R46_P4_MAP_WORDS = 38 * 21,
    R46_P4_TILE_BYTES = 32,
    R46_P4_FONT_FIRST_TILE = 1696,
    R46_P4_ROW_BASE = 38
};

#if defined(DOOM_R46_M1B)
/* All functions read framebuffer as if pixel4 owned the existing _s_screen.
 * They MUST NOT be called during active 8x8 rendering. The sole exception
 * is R46_P4_VramValidate(), which uses metadata and constants only. */
uint16_t R46_P4_TileAt(uint16_t bank,uint16_t column,uint16_t row);
uint16_t R46_P4_MapRow(uint16_t bank,uint16_t row,uint16_t output[R46_P4_COLUMNS]);
void R46_P4_PatternRows(uint16_t column,uint16_t row,uint32_t output[8]);
uint16_t R46_P4_VramValidate(void);
#endif
#endif
