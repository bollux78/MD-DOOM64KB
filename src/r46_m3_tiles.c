/* R46 M3A: caller-memory tile map/32-byte patterns, bit-identical to
 * prior M1B VRAM packing contract. Hardware VDP is NOT accessed.
 */
#if defined(DOOM_R46_M2C)
#include "r46_m3_tiles.h"
#include "r46_pixel4_vram.h"
#include "r22_pixel4.h"
#if !defined(DOOM_R46_M2B) || !defined(DOOM_R46_M1B) || defined(DOOM_R22_PIXEL4)
#error M3A tiles need M1B/M2B native coexistence beside R39f
#endif
_Static_assert((int)R46_M3_TILES_COLUMNS==(int)R46_P4_COLUMNS &&
               (int)R46_M3_TILES_ROWS==(int)R46_P4_ROWS &&
               (int)R46_M3_TILES_PER_BANK==(int)R46_P4_BANK_TILES &&
               R46_P4_FONT_FIRST_TILE==1696,
               "M3A tile bank layout drift");
static uint16_t valid_tile(const uint8_t *packed,uint16_t capacity,
                           uint16_t bank,uint16_t x,uint16_t row)
{
    return (uint16_t)(packed && capacity>=R46_P4_RASTER_BYTES &&
        bank<=1u && x<R46_M3_TILES_COLUMNS &&
        row>=1u && row<=R46_M3_TILES_ROWS);
}
uint16_t R46_M3_TileAt(const uint8_t *p,uint16_t capacity,
    uint16_t bank,uint16_t x,uint16_t row)
{
    if(!valid_tile(p,capacity,bank,x,row))return 0xffffu;
    const uint16_t offset=(uint16_t)(row*2u*R46_P4_RASTER_PITCH+x);
    const uint16_t dynamic=(uint16_t)(R46_P4_SOLID_TILES+
         bank*R46_P4_BANK_TILES+R46_P4_ROW_BASE+
         (row-1u)*R46_M3_TILES_COLUMNS+x);
    return R22_TileIndex(p[offset],p[offset+R46_P4_RASTER_PITCH],
                         dynamic);
}
uint16_t R46_M3_MapRow(const uint8_t *p,uint16_t capacity,
    uint16_t bank,uint16_t row,uint16_t out[38])
{
    if(!out||!valid_tile(p,capacity,bank,0,row))return 0;
    for(uint16_t x=0;x<R46_M3_TILES_COLUMNS;x++)
        out[x]=R46_M3_TileAt(p,capacity,bank,x,row);
    return R46_M3_TILES_COLUMNS;
}
uint16_t R46_M3_PackDynamic(const uint8_t *p,uint16_t capacity,
    uint16_t bank,uint16_t x,uint16_t row,uint32_t out[8])
{
    if(!out)return 0;
    const uint16_t tile=R46_M3_TileAt(p,capacity,bank,x,row);
    if(tile==0xffffu||tile<R46_P4_SOLID_TILES)return 0;
    const uint16_t pos=(uint16_t)(row*2u*R46_P4_RASTER_PITCH+x);
    const uint32_t upper=R22_ExpandPair(p[pos]);
    const uint32_t lower=R22_ExpandPair(p[pos+R46_P4_RASTER_PITCH]);
    for(uint16_t y=0;y<4;y++){out[y]=upper;out[y+4]=lower;}
    return tile;
}
uint16_t R46_M3_PackOwned(const r46_m3_owner_t *owner,
    const uint8_t *p,uint16_t capacity,
    uint16_t bank,uint16_t column,uint16_t row,uint32_t out[8])
{
    if(!R46_M3_MayWrite(owner,R46_M3_PIXEL4))return 0;
    return R46_M3_PackDynamic(p,capacity,bank,column,row,out);
}
typedef struct {
    uint16_t (*tile)(const uint8_t*,uint16_t,uint16_t,uint16_t,uint16_t);
    uint16_t (*map)(const uint8_t*,uint16_t,uint16_t,uint16_t,uint16_t*);
    uint16_t (*pack)(const uint8_t*,uint16_t,uint16_t,uint16_t,uint16_t,uint32_t*);
    uint16_t (*owned)(const r46_m3_owner_t*,const uint8_t*,uint16_t,
                      uint16_t,uint16_t,uint16_t,uint32_t*);
} r46_m3_tiles_ops_t;
static const r46_m3_tiles_ops_t tiles_ops={
    R46_M3_TileAt,R46_M3_MapRow,R46_M3_PackDynamic,R46_M3_PackOwned
};
__attribute__((noinline))
const r46_m3_tiles_ops_t *R46_M3_TilesOps(void){return &tiles_ops;}
__attribute__((noinline))
uint16_t R46_M3_TilesValidate(void)
{
    const r46_m3_tiles_ops_t *ops=R46_M3_TilesOps();
    return (uint16_t)(ops && ops->tile && ops->map &&
        ops->pack && ops->owned && R46_P4_RASTER_BYTES==1672 &&
        R46_P4_FONT_FIRST_TILE>1687);
}
#endif
