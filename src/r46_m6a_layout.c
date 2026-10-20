/* R46 M6A: metadata-only oracle, no VRAM/CRAM access, no heap.
 * IMPORTANT: R6A merely proves proposed addresses. The legacy SGDK
 * ROM renderer must not load tile indices from these constants yet.
 */
#include "r46_m6a_layout.h"

uint16_t R46_M6A_DynamicTile(uint16_t bank,uint16_t col,uint16_t row)
{
    if(bank>=R46_M6A_BANK_COUNT || col>=R46_M6A_COLUMN_COUNT ||
       row==0u || row>R46_M6A_DYNAMIC_ROWS)return 0xffffu;
    return (uint16_t)(R46_M6A_BANK0_DYNAMIC_FIRST +
                      bank * R46_M6A_BANK_STRIDE +
                      (row-1u)*R46_M6A_COLUMN_COUNT + col);
}

__attribute__((noinline))
uint16_t R46_M6A_LayoutValidate(void)
{
    const uint16_t lastPattern=(uint16_t)(R46_M6A_BANK1_DYNAMIC_LAST+1u);
    const uint16_t mapTileBase=(uint16_t)(R46_M6A_MAP_A/32u);
    const uint16_t hscrollTileBase=(uint16_t)(R46_M6A_HSCROLL/32u);
    const uint16_t spriteTileBase=(uint16_t)(R46_M6A_SAT/32u);
    return (uint16_t)(
        R46_M6A_DynamicTile(0u,0u,1u)==150u &&
        R46_M6A_DynamicTile(0u,37u,21u)==947u &&
        R46_M6A_DynamicTile(1u,0u,1u)==986u &&
        R46_M6A_DynamicTile(1u,37u,21u)==1783u &&
        R46_M6A_DynamicTile(2u,0u,1u)==0xffffu &&
        R46_M6A_DynamicTile(0u,38u,1u)==0xffffu &&
        R46_M6A_DynamicTile(0u,0u,0u)==0xffffu &&
        lastPattern<=mapTileBase && mapTileBase==1792u &&
        mapTileBase+128u<=hscrollTileBase &&
        hscrollTileBase+32u<=spriteTileBase &&
        spriteTileBase+32u<=2048u &&
        R46_M6A_MAP_B==R46_M6A_MAP_A &&
        R46_M6A_WINDOW==R46_M6A_MAP_A &&
        R46_M6A_VBLANK_BYTES==7200u);
}
