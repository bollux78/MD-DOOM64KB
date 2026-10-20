/* R46 M3B: first isolated REAL native pixel4 VDP presentation.
 * BOOT DIAGNOSTIC ONLY, not the DOOM renderer or a live mode toggle.
 *
 * This route draws one 76x44 packed frame, uploads 798 dynamic bank0 tiles
 * through CPU writes, displays it for 120 VBlanks, then restores all R39f
 * 8x8 palette/patterns/name-table state before gameplay begins.
 *
 * No large WRAM buffers: 1672 pixels borrow 2128-byte _s_screen exclusively
 * after R20's pending VBlank snapshot has drained. 76-byte map-row and
 * 32-byte pattern scratch reside on stack. Plane A remains at its 8x8
 * 64x32 address, so BANK0 ends well before 0xC000 and cannot overwrite it.
 */
#if defined(DOOM_R46_M3B_DIAG)
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "i_system.h"
#include "r20_dma.h"
#include "r22_palette.h"
#include "r46_m3b_video.h"
#include "r46_m3b_pattern.h"
#include "r46_m3_owner.h"
#include "r46_m3_tiles.h"
#include "r46_pixel4_vram.h"
#if !defined(DOOM_R46_M2C) || defined(DOOM_R22_PIXEL4)
#error M3B diagnostic only runs with staged dual-linked cell/P4 build
#endif
static void m3b_expect(uint16_t success,const char *reason)
{
    if(!success)I_Error("R46 M3B: %s",reason);
}
__attribute__((noinline))
void R46_M3B_ShowVideoTest(uint16_t *backing,
                           void (*reload_cell_tiles)(void),
                           void (*restore_cell_palette)(void))
{
    m3b_expect(backing && reload_cell_tiles && restore_cell_palette,
               "missing caller-owned resources");
    r46_m3_owner_t owner;
    R46_M3_OwnerInit(&owner);
    m3b_expect(R46_M3_Request(&owner,R46_M3_PIXEL4),"request pixel4");

    /* R20's VBlank ISR is still installed for system/XGM services, but
     * after Stop/Abort it cannot publish an old snapshot. No producer
     * runs during this blocking boot diagnostic. */
    R20_StopVideo();
    VDP_waitDMACompletion();
    m3b_expect(R46_M3_AckQuiesce(&owner,R46_M3_DMA_DRAINED),
               "DMA barrier");
    R20_AbortVideo();
    m3b_expect(R46_M3_AckQuiesce(&owner,R46_M3_IRQ_DISABLED),
               "retired old-frame ISR access");
    m3b_expect(!R46_M3_MayWrite(&owner,R46_M3_CELL),
               "cell owner still active");

    /* BANK0 occupies tiles 54..851 = 0x06C0..0x6A7F in VRAM.
     * Primary 8x8 Plane A name table at 0xC000 is NOT relocated, and
     * the font remains at its original SGDK address near 0xD400.
     * We will restore its dither/checker patterns before 8x8 resumes. */
    VDP_setAutoInc(2);
    VDP_setTextPlane(BG_A);
    VDP_clearPlane(BG_A,TRUE);
    VDP_waitDMACompletion();
    m3b_expect(R46_M3_AckReconfigure(&owner,R46_M3_VRAM_READY),
               "bank0 reserved");

    PAL_setColors(0,r22_cram[0],16,CPU);
    m3b_expect(R46_M3_AckReconfigure(&owner,R46_M3_CRAM_READY),
               "pixel4 palette ready");
    m3b_expect(R46_M3_AckReconfigure(&owner,R46_M3_MAP_READY),
               "plane A cleared");
    m3b_expect(R46_M3_Commit(&owner),"commit pixel4");
    m3b_expect(R46_M3_MayWrite(&owner,R46_M3_PIXEL4),
               "pixel4 ownership rejected");

    uint8_t *pixels=(uint8_t *)(void *)backing;
    m3b_expect(R46_M3B_MakePattern(pixels,1672),"create packed frame");
    uint16_t row_map[38];
    uint32_t packed_tile[8];
    for(uint16_t y=1;y<=21;y++){
        for(uint16_t x=0;x<38;x++){
            uint16_t tile=R46_M3_PackOwned(&owner,pixels,1672,
                                           0,x,y,packed_tile);
            /* Synthetic even/odd colors guarantee every tile is dynamic.
             * This avoids using the 0..15 SGDK/system tile indices. */
            m3b_expect(tile>=54 && tile<=851,"non-dynamic tile");
            row_map[x]=tile;
            VDP_loadTileData(packed_tile,tile,1,CPU);
        }
        VDP_setTileMapDataRect(BG_A,row_map,0,y,38,1,38,CPU);
    }
    VDP_drawText("R46 M3B 4X4 VIDEO TEST",1,0);
    VDP_waitDMACompletion();
    for(uint16_t i=0;i<120;i++)SYS_doVBlankProcess();

    /* Reverse handoff. Nobody may draw a pixel4 or R39f frame until
     * the old P4 bank/palette/map and DMA have been retired. */
    m3b_expect(R46_M3_Request(&owner,R46_M3_CELL),"request cell");
    VDP_waitDMACompletion();
    m3b_expect(R46_M3_AckQuiesce(&owner,R46_M3_DMA_DRAINED),
               "pixel4 DMA barrier");
    m3b_expect(R46_M3_AckQuiesce(&owner,R46_M3_IRQ_DISABLED),
               "pixel4 IRQ barrier");
    VDP_clearPlane(BG_A,TRUE);
    VDP_waitDMACompletion();
    reload_cell_tiles(); /* Restore ALL 8x8 checker/stripe tiles overwritten. */
    m3b_expect(R46_M3_AckReconfigure(&owner,R46_M3_VRAM_READY),
               "cell dither tiles");
    restore_cell_palette();
    VDP_waitDMACompletion();
    m3b_expect(R46_M3_AckReconfigure(&owner,R46_M3_CRAM_READY),
               "cell palette");
    m3b_expect(R46_M3_AckReconfigure(&owner,R46_M3_MAP_READY),
               "cell map cleared");
    m3b_expect(R46_M3_Commit(&owner),"commit cell");
    m3b_expect(R46_M3_MayWrite(&owner,R46_M3_CELL),
               "cell owner not restored");
    VDP_setAutoInc(2);
}
#endif
