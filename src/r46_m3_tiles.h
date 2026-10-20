/* R46 M3A: convert a caller-owned packed 76x44 frame to VRAM tiles.
 * No global _s_screen read, no VDP writes or additional framebuffer.
 */
#ifndef R46_M3_TILES_HEADER_H
#define R46_M3_TILES_HEADER_H
#include <stdint.h>
#include "r46_m3_owner.h"
#include "r46_pixel4_raster.h"
enum { R46_M3_TILES_COLUMNS=38, R46_M3_TILES_ROWS=21,
       R46_M3_TILES_PER_BANK=836, R46_M3_TILES_OUTPUT=8 };
#if defined(DOOM_R46_M2C)
/* Return 0xFFFF for an invalid location, otherwise a solid index (0..15)
 * or the native dynamic VRAM tile index (bank0:54..851, bank1:890..1687).
 * row=1..21 maps pixel rows 2..43, reserving top two sample rows. */
uint16_t R46_M3_TileAt(const uint8_t *packed,uint16_t capacity,
    uint16_t bank,uint16_t column,uint16_t row);
uint16_t R46_M3_MapRow(const uint8_t *packed,uint16_t capacity,
    uint16_t bank,uint16_t row,uint16_t output[38]);
/* Dynamic tile: expand two packed pixel bytes into eight 32-bit 4bpp
 * scanlines; return dynamic index. Solid/invalid: return 0 and do
 * not modify caller's eight pattern words. */
uint16_t R46_M3_PackDynamic(const uint8_t *packed,uint16_t capacity,
    uint16_t bank,uint16_t column,uint16_t row,uint32_t output[8]);
/* Requires real, committed pixel4 exclusive ownership BEFORE accessing
 * packed shared-frame memory. Does not itself change registers or upload. */
uint16_t R46_M3_PackOwned(const r46_m3_owner_t *owner,
    const uint8_t *packed,uint16_t capacity,
    uint16_t bank,uint16_t column,uint16_t row,uint32_t output[8]);
uint16_t R46_M3_TilesValidate(void);
#endif
#endif
