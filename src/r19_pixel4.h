/* R19 experimental 4x4 logical-pixel output for the Mega Drive H40 VDP.
 * 80x44 logical pixels -> 40x22 unique 8x8 tile patterns.
 * Based on the existing Doom column renderer and the Doom8088 low-res idea.
 * Copyright (C) 2026 MD-DOOM64KB contributors; GPL-2.0-or-later.
 * This header is included ONLY from i_genesisv.c with DOOM_R19_PIXEL4. */
#ifndef DOOM_R19_PIXEL4
#error r19_pixel4.h is experimental and must not be included by R18
#endif
#if VIEWWINDOWWIDTH != 80 || VIEWWINDOWHEIGHT != 44
#error R19 expects VIEWWINDOWWIDTH=80 and VIEWWINDOWHEIGHT=44
#endif
#define R19_BLACK_SLOT GENPAL_NVIEW
#define R19_TILE_BASE (SOLID_TILE_INDEX + 16)

/* Keep the large 28 KiB pattern set in VRAM, not work RAM. */
static uint8_t r19_pixels[VIEWWINDOWWIDTH * VIEWWINDOWHEIGHT];
static uint32_t r19_tile_row[20 * 8]; /* 640-byte DMA staging, two transfers/row */
static uint8_t r19_nearest[4][GENPAL_NVIEW + 1];
static uint8_t r19_cost[4][GENPAL_NVIEW + 1];

/* Palette choice is per tile: all four logical pixels must share one
 * VDP palette. Precompute closest color and 3-bit RGB error for every
 * one of the 56 source slots, in each of the four 16-color palettes. */
static void R19_InitPaletteMapping(void)
{
    for (uint16_t slot = 0; slot < GENPAL_NVIEW; slot++)
    {
        uint16_t src = genpal_cram[0][(slot / GENPAL_VIEW_PER_PAL) * 16
                                     + 1 + (slot % GENPAL_VIEW_PER_PAL)];
        for (uint16_t pal = 0; pal < 4; pal++)
        {
            uint16_t best_cost = 65535, best_idx = 0;
            for (uint16_t idx = 0; idx < 15; idx++)
            {
                uint16_t dst = genpal_cram[0][pal * 16 + idx];
                int16_t dr = (int16_t)((src >> 1) & 7) - (int16_t)((dst >> 1) & 7);
                int16_t dg = (int16_t)((src >> 5) & 7) - (int16_t)((dst >> 5) & 7);
                int16_t db = (int16_t)((src >> 9) & 7) - (int16_t)((dst >> 9) & 7);
                uint16_t error = (uint16_t)(dr*dr + dg*dg + db*db);
                if (error < best_cost) { best_cost = error; best_idx = idx; }
            }
            r19_nearest[pal][slot] = (uint8_t)best_idx;
            r19_cost[pal][slot] = (uint8_t)best_cost;
        }
    }
    for (uint16_t pal = 0; pal < 4; pal++)
    {
        r19_nearest[pal][R19_BLACK_SLOT] = 0;
        r19_cost[pal][R19_BLACK_SLOT] = 0;
    }
}

static void R19_ResetTilemap(void)
{
    for (uint16_t y = 0; y < VDP_VIEW_ROWS; y++)
        for (uint16_t x = 0; x < VDP_MAP_COLS; x++)
            _s_screen[y * VDP_MAP_COLS + x] =
                TILE_ATTR_FULL(0, 0, 0, 0, R19_TILE_BASE + y * VDP_MAP_COLS + x);
}

/* Invoked before menus draw, preserving menu font tiles. */
void R19_PrepareFrame(void)
{
    R19_ResetTilemap();
}

static void R19_UploadPixels(void)
{
    for (uint16_t y = 0; y < VDP_VIEW_ROWS; y++)
    {
        uint16_t src_top = (y * 2) * VIEWWINDOWWIDTH;
        uint16_t src_bottom = src_top + VIEWWINDOWWIDTH;
        for (uint16_t x = 0; x < VDP_MAP_COLS; x++)
        {
            uint16_t sx = x * 2;
            uint8_t a = r19_pixels[src_top + sx];
            uint8_t b = r19_pixels[src_top + sx + 1];
            uint8_t c = r19_pixels[src_bottom + sx];
            uint8_t d = r19_pixels[src_bottom + sx + 1];
            uint16_t best_error = 65535, best_pal = 0;
            for (uint16_t pal = 0; pal < 4; pal++)
            {
                uint16_t error = (uint16_t)r19_cost[pal][a] + r19_cost[pal][b]
                               + r19_cost[pal][c] + r19_cost[pal][d];
                if (error < best_error) { best_error = error; best_pal = pal; }
            }
            const uint8_t *m = r19_nearest[best_pal];
            uint32_t top = ((uint32_t)(m[a] * 0x1111u) << 16)
                         | (uint32_t)(m[b] * 0x1111u);
            uint32_t bottom = ((uint32_t)(m[c] * 0x1111u) << 16)
                            | (uint32_t)(m[d] * 0x1111u);
            uint32_t *tile = &r19_tile_row[(x % 20) * 8];
            tile[0] = top; tile[1] = top; tile[2] = top; tile[3] = top;
            tile[4] = bottom; tile[5] = bottom; tile[6] = bottom; tile[7] = bottom;
            if ((x % 20) == 19)
                VDP_loadTileData(r19_tile_row,
                                 R19_TILE_BASE + y * VDP_MAP_COLS + x - 19,
                                 20, DMA);
            /* Keep text overlay intact: the tilemap was reset before M_Drawer.
             * Only change the palette bits for entries still pointing at
             * the R19 pattern assigned to this screen position. */
            uint16_t old = _s_screen[y * VDP_MAP_COLS + x];
            if ((old & 0x7ff) == R19_TILE_BASE + y * VDP_MAP_COLS + x)
                _s_screen[y * VDP_MAP_COLS + x] =
                    TILE_ATTR_FULL(best_pal, 0, 0, 0,
                                   R19_TILE_BASE + y * VDP_MAP_COLS + x);
        }
    }
}
