/* R46 M6A: prospective fixed-font VRAM layout for 64x32 H40.
 * This header is a PURE CONTRACT. It never programs the VDP and is
 * not a signal to change the SGDK ABI or currently running R5 pixels.
 *
 * The pinned MarsDev SGDK revision (cb114acadc45) uses legacy font
 * placement. R6B must build a separate matching SGDK library and
 * headers before enabling this layout on real hardware.
 */
#ifndef R46_M6A_LAYOUT_H
#define R46_M6A_LAYOUT_H
#include <stdint.h>

enum {
    R46_M6A_TOTAL_VRAM_BYTES = 65536,
    R46_M6A_TILE_BYTES = 32,
    R46_M6A_SYSTEM_TILES = 16,
    R46_M6A_FONT_TILES = 96,
    R46_M6A_FIXED_FONT_FIRST = 16,
    R46_M6A_FIXED_FONT_LAST = 111,
    R46_M6A_USER_FIRST = 112,
    R46_M6A_BANK_COUNT = 2,
    R46_M6A_COLUMN_COUNT = 38,
    R46_M6A_DYNAMIC_ROWS = 21,
    R46_M6A_DYNAMIC_TILES = R46_M6A_COLUMN_COUNT * R46_M6A_DYNAMIC_ROWS,
    /* Retain the tested 836-tile stride and 38-tile row offset.
     * Replacing this with compact 798-tile strides would silently
     * change the M1B/M3A packer contract and overlap solid tiles. */
    R46_M6A_BANK_STRIDE = 836,
    R46_M6A_ROW_BASE = 38,
    R46_M6A_BANK0_DYNAMIC_FIRST = R46_M6A_USER_FIRST + R46_M6A_ROW_BASE,
    R46_M6A_BANK0_DYNAMIC_LAST = R46_M6A_BANK0_DYNAMIC_FIRST + R46_M6A_DYNAMIC_TILES - 1,
    R46_M6A_BANK1_DYNAMIC_FIRST = R46_M6A_BANK0_DYNAMIC_FIRST + R46_M6A_BANK_STRIDE,
    R46_M6A_BANK1_DYNAMIC_LAST = R46_M6A_BANK1_DYNAMIC_FIRST + R46_M6A_DYNAMIC_TILES - 1,
    R46_M6A_MAP_A = 0xE000,
    R46_M6A_MAP_B = 0xE000, /* aliases A only while future M6 pixel4 owns VDP */
    R46_M6A_WINDOW = 0xE000, /* Window inactive or aliases BG_A */
    R46_M6A_HSCROLL = 0xF000,
    R46_M6A_SAT = 0xF400,
    R46_M6A_VISIBLE_TILES = R46_M6A_COLUMN_COUNT * R46_M6A_DYNAMIC_ROWS,
    R46_M6A_VBLANK_BYTES = 7200
};

_Static_assert(R46_M6A_FIXED_FONT_FIRST == R46_M6A_SYSTEM_TILES,"SGDK system/font overlap");
_Static_assert(R46_M6A_FIXED_FONT_LAST + 1 == R46_M6A_USER_FIRST,"SGDK user start mismatch");
_Static_assert(R46_M6A_BANK_STRIDE == 836,"R22 bank slot drift");
_Static_assert(R46_M6A_BANK0_DYNAMIC_FIRST == 150 && R46_M6A_BANK0_DYNAMIC_LAST == 947,"bank0 tile indices");
_Static_assert(R46_M6A_BANK1_DYNAMIC_FIRST == 986 && R46_M6A_BANK1_DYNAMIC_LAST == 1783,"bank1 tile indices");
_Static_assert((R46_M6A_BANK1_DYNAMIC_LAST + 1)*R46_M6A_TILE_BYTES == 0xDF00,
               "bank1 end must remain below plane A E000");
_Static_assert(R46_M6A_MAP_A % 0x2000 == 0 && R46_M6A_MAP_B % 0x2000 == 0,
               "VDP plane table alignment");
_Static_assert(R46_M6A_WINDOW % 0x1000 == 0,"H40 window alignment");
_Static_assert(R46_M6A_SAT % 0x400 == 0 && R46_M6A_HSCROLL % 0x400 == 0,"VDP table alignment");

uint16_t R46_M6A_DynamicTile(uint16_t bank,uint16_t column,uint16_t row);
uint16_t R46_M6A_LayoutValidate(void);
#endif
