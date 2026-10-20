/* R46 M1B: map and pack 76x44 native samples to the R44-approved
 * two-bank VRAM layout, WITHOUT writes to hardware or extra tilemap BSS.
 *
 * R22 standalone uploads all dynamic patterns in the main loop, then
 * DMA-flips the prepared 38x21 tilemap during VBlank. This module ONLY
 * prepares the same patterns/map on demand. M2/M3 must provide safe
 * exclusive ownership, upload scheduling, DMA barrier and 8x8<->4x4
 * VDP/CRAM transitions before any of the drawing helpers are called.
 */
#if defined(DOOM_R46_M1B)
#include <stddef.h>
#include <stdint.h>
#include "r22_pixel4.h"
#include "r46_pixel4_vram.h"

#if !defined(DOOM_R46_M1) || !defined(DOOM_R20_REG_COLUMNS) || defined(DOOM_R22_PIXEL4)
#error R46 M1B requires dual-linked pixel4 helpers beside primary R39f cell
#endif

/* R20 tileword framebuffer: its first 1672 bytes become the P4 pixels
 * ONLY when the future renderer-ownership dispatcher grants the buffer. */
extern uint16_t _s_screen[38 * 28];

_Static_assert(R22_W==76 && R22_H==44, "R46 P4 geometry drift");
_Static_assert(R22_PITCH==38 && R22_FB_BYTES==1672, "R46 P4 packed stride drift");
_Static_assert(R22_TILES==836 && R46_P4_BANK_TILES==R22_TILES, "R46 P4 tile-bank drift");
_Static_assert(sizeof(_s_screen)==2128, "R46 P4 shared framebuffer drift");

static inline const uint8_t *R46_P4_Frame(void)
{
    return (const uint8_t *)(const void *)_s_screen;
}
static inline uint16_t R46_P4_DynamicTile(uint16_t bank,uint16_t column,uint16_t row)
{
    /* Row0 remains the persistent FPS/text row; graphical y=1..21
     * correspond to framebuffer samples y=2..43. */
    return (uint16_t)(R46_P4_SOLID_TILES
           +bank*R46_P4_BANK_TILES+R46_P4_ROW_BASE
           +(row-1u)*R46_P4_COLUMNS+column);
}
uint16_t R46_P4_TileAt(uint16_t bank,uint16_t column,uint16_t row)
{
    if(bank>1u||column>=R46_P4_COLUMNS||row==0u||row>R46_P4_ROWS)
        return 0;
    const uint8_t *p=R46_P4_Frame();
    const uint16_t offset=(uint16_t)(row*2u*R22_PITCH+column);
    const uint8_t upper=p[offset];
    const uint8_t lower=p[offset+R22_PITCH];
    return R22_TileIndex(upper,lower,R46_P4_DynamicTile(bank,column,row));
}
uint16_t R46_P4_MapRow(uint16_t bank,uint16_t row,uint16_t output[R46_P4_COLUMNS])
{
    if(!output||bank>1u||row==0u||row>R46_P4_ROWS)
        return 0;
    for(uint16_t x=0;x<R46_P4_COLUMNS;x++)
        output[x]=R46_P4_TileAt(bank,x,row);
    return R46_P4_COLUMNS;
}
void R46_P4_PatternRows(uint16_t column,uint16_t row,uint32_t output[8])
{
    if(!output)return;
    if(column>=R46_P4_COLUMNS||row==0u||row>R46_P4_ROWS){
        for(uint16_t y=0;y<8;y++)output[y]=0;
        return;
    }
    const uint8_t *p=R46_P4_Frame();
    const uint16_t offset=(uint16_t)(row*2u*R22_PITCH+column);
    const uint32_t upper=R22_ExpandPair(p[offset]);
    const uint32_t lower=R22_ExpandPair(p[offset+R22_PITCH]);
    for(uint16_t y=0;y<4;y++){
        output[y]=upper;
        output[y+4]=lower;
    }
}
/* Q3 preparation: avoid both pattern expansion and future VDP writes
 * for immutable one-color tiles.  A nonzero return is the dynamic tile
 * index, not a byte count; the caller can defer the VDP address command
 * until AFTER this returns a dynamic index.  No IRQ/VDP access here. */
uint16_t R46_P4_PackIfDynamic(uint16_t bank,uint16_t column,uint16_t row,
                              uint32_t output[8])
{
    if(!output)return 0;
    const uint16_t tile=R46_P4_TileAt(bank,column,row);
    if(tile<R46_P4_SOLID_TILES)return 0;
    R46_P4_PatternRows(column,row,output);
    return tile;
}
static const r46_p4_vram_ops_t r46_p4_vram_ops = {
    R46_P4_TileAt,R46_P4_MapRow,R46_P4_PatternRows,
    R46_P4_PackIfDynamic
};
__attribute__((noinline))
const r46_p4_vram_ops_t *R46_P4_VramOps(void)
{
    return &r46_p4_vram_ops;
}
__attribute__((noinline))
uint16_t R46_P4_VramValidate(void)
{
    /* Metadata-only: it can be called while the active renderer is 8x8.
     * Pixel/TileAt/PatternRows are NOT safe until pixel4 owns _s_screen. */
    const uint16_t bank0first=(uint16_t)(R46_P4_SOLID_TILES+R46_P4_ROW_BASE);
    const uint16_t bank1first=(uint16_t)(bank0first+R46_P4_BANK_TILES);
    const uint16_t bank1last=(uint16_t)(bank1first+R46_P4_MAP_WORDS-1u);
    const r46_p4_vram_ops_t *ops=R46_P4_VramOps();
    return (uint16_t)(ops && ops->tile_at && ops->map_row && ops->pattern_rows && ops->pack_if_dynamic &&
                      R46_P4_MAP_WORDS==798u &&
                      R46_P4_ROWS*2u+2u==R22_H &&
                      R46_P4_COLUMNS*2u==R22_W &&
                      bank0first==54u && bank1first==890u &&
                      bank1last==1687u &&
                      bank1last<R46_P4_FONT_FIRST_TILE &&
                      R22_FB_BYTES<=sizeof(_s_screen));
}
#endif
