/* R46 M3C: 4-phase real VDP dual-pattern-bank diagnostic.
 * Two pattern banks (54..851 and 890..1687) are displayed in alternation.
 * BANK 1 OVERLAPS THE OLD BG_A NAME TABLE AT 0xC000: the diagnostic
 * MUST relocate BG_A to 0xE000 before uploading bank 1, and restore
 * 0xC000 plus 8x8 cell patterns before returning to gameplay.
 *
 * Genesis H40 64x32 BG_A maps require 0x2000 alignment, so 0xE000 is
 * the only available map during dual-bank test; no atomic two-map flip
 * is possible with this layout. For each swap, the CPU uploads the
 * hidden bank, blanks display, replaces all 21 map rows, syncs to a
 * VBlank, and reenables display. Blank frames are expected; a mixed
 * bank tilemap must NEVER be presented. This is NOT a zero-blanking flip.
 *
 * No heap and NO second framebuffer. _s_screen backing is borrowed
 * only while the R39f VBlank publisher is stopped.
 */
#if defined(DOOM_R46_M3C_DIAG)
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "i_system.h"
#include "r20_dma.h"
#include "r22_palette.h"
#include "r46_m3c_video.h"
#include "r46_m3c_bank.h"
#include "r46_m3c_pattern.h"
#include "r46_m3_owner.h"
#include "r46_m3_tiles.h"
#include "r46_pixel4_vram.h"
#if !defined(DOOM_R46_M2C) || defined(DOOM_R46_M3B_DIAG) || defined(DOOM_R22_PIXEL4)
#error M3C requires isolated staged pixel4/video diagnostic build
#endif
static void m3c_expect(uint16_t ok,const char *message)
{
    if(!ok)I_Error("R46 M3C: %s",message);
}
static void m3c_upload_hidden_bank(r46_m3_owner_t *owner,
    r46_m3c_bank_t *stage,uint8_t *pixels,uint16_t bank)
{
    uint32_t tile_words[8];
    m3c_expect(R46_M3C_BankWritable(stage,bank),"bank is visible/locked");
    for(uint16_t y=1;y<=21;y++){
        for(uint16_t x=0;x<38;x++){
            uint16_t tile=R46_M3_PackOwned(owner,pixels,1672,
                                           bank,x,y,tile_words);
            m3c_expect(tile>=54 && tile<=1687,
                       "tile out of double bank space");
            VDP_loadTileData(tile_words,tile,1,CPU);
        }
        m3c_expect(R46_M3C_TilesUploaded(stage,38),"tile upload counter");
    }
    m3c_expect(stage->uploaded==798,"incomplete hidden bank");
}
static void m3c_swap_map_while_blanked(r46_m3_owner_t *owner,
    r46_m3c_bank_t *stage,uint8_t *pixels,uint16_t bank)
{
    uint16_t row_map[38];
    /* VBlank gate BEFORE changing the VDP visible map. No partial map
     * is visible while VDP display is disabled. */
    SYS_doVBlankProcess();
    VDP_setEnable(FALSE);
    VDP_waitDMACompletion();
    for(uint16_t y=1;y<=21;y++){
        m3c_expect(R46_M3_MapRow(pixels,1672,bank,y,row_map)==38,
                   "map row generation");
        VDP_setTileMapDataRect(BG_A,row_map,0,y,38,1,38,CPU);
        m3c_expect(R46_M3C_MapRowWritten(stage,y),
                   "row stage acknowledgement");
    }
    VDP_drawText(bank ? "R46 M3C 4X4 BANK 1" : "R46 M3C 4X4 BANK 0",1,0);
    VDP_waitDMACompletion();
    /* Commit only after an additional VBlank while the screen is black. */
    SYS_doVBlankProcess();
    m3c_expect(R46_M3_MayWrite(owner,R46_M3_PIXEL4),
               "pixel4 owner unexpectedly retired");
    m3c_expect(R46_M3C_CommitBank(stage,1),"incomplete map flip");
    VDP_setEnable(TRUE);
}
__attribute__((noinline))
void R46_M3C_ShowVideoTest(uint16_t *backing,
                           void (*reload_cell_tiles)(void),
                           void (*restore_cell_palette)(void))
{
    m3c_expect(backing && reload_cell_tiles && restore_cell_palette,
               "invalid shared frame/restore callbacks");
    r46_m3_owner_t owner;
    r46_m3c_bank_t banks;
    R46_M3_OwnerInit(&owner);
    R46_M3C_BankInit(&banks);
    m3c_expect(R46_M3_Request(&owner,R46_M3_PIXEL4),"request pixel4");
    R20_StopVideo();
    VDP_waitDMACompletion();
    m3c_expect(R46_M3_AckQuiesce(&owner,R46_M3_DMA_DRAINED),
               "drain prior cell DMA");
    R20_AbortVideo();
    m3c_expect(R46_M3_AckQuiesce(&owner,R46_M3_IRQ_DISABLED),
               "retire cell video ISR writer");
    m3c_expect(!R46_M3_MayWrite(&owner,R46_M3_CELL),
               "old cell owner still active");
    /* 1688 patterns * 32 = 0xD300; below the SGDK font at 0xD400.
     * Old BG_A at 0xC000 IS overlapped by bank 1. Temporarily put
     * 64x32 BG_A (4 KiB) at E000..EFFF, which no dynamic tile touches. */
    m3c_expect(1688u*32u<=0xD400u && 0xE000u>1688u*32u,
               "VRAM layout overlap");
    m3c_expect(VDP_getBGAAddress()==0xC000u,"unexpected BG_A base");
    VDP_setEnable(FALSE);
    VDP_setAutoInc(2);
    VDP_setBGAAddress(0xE000u);
    VDP_setTextPlane(BG_A);
    VDP_clearPlane(BG_A,TRUE);
    VDP_waitDMACompletion();
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_VRAM_READY),
               "relocate BG_A");
    PAL_setColors(0,r22_cram[0],16,CPU);
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_CRAM_READY),
               "pixel4 diagnostic palette");
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_MAP_READY),
               "clear relocated map");
    m3c_expect(R46_M3_Commit(&owner),"commit pixel4");
    m3c_expect(R46_M3_MayWrite(&owner,R46_M3_PIXEL4),
               "pixel4 owner unavailable");

    uint8_t *pixels=(uint8_t *)(void*)backing;
    for(uint16_t phase=0;phase<4;phase++){
        const uint16_t bank=(uint16_t)(phase&1u);
        m3c_expect(R46_M3C_StageBank(&banks,bank),"stage hidden bank");
        m3c_expect(R46_M3C_BankWritable(&banks,bank),"visible bank hazard");
        m3c_expect(R46_M3C_MakePattern(pixels,1672,phase),
                   "phase pattern generation");
        /* Only the NOT currently visible bank receives tile patterns.
         * Starting phase 0 runs with display off; subsequent hidden-bank
         * uploads can run with the prior bank still visible. */
        m3c_upload_hidden_bank(&owner,&banks,pixels,bank);
        m3c_swap_map_while_blanked(&owner,&banks,pixels,bank);
        for(uint16_t frame=0;frame<45;frame++)SYS_doVBlankProcess();
    }

    /* Restore the R39f framebuffer owner and all overwritten VRAM. */
    m3c_expect(R46_M3_Request(&owner,R46_M3_CELL),"request 8x8");
    VDP_setEnable(FALSE);
    VDP_waitDMACompletion();
    m3c_expect(R46_M3_AckQuiesce(&owner,R46_M3_DMA_DRAINED),
               "drain pixel4 DMA");
    m3c_expect(R46_M3_AckQuiesce(&owner,R46_M3_IRQ_DISABLED),
               "retire pixel4 display");
    VDP_clearPlane(BG_A,TRUE); /* Clear relocated BG_A / BG_B E000. */
    VDP_waitDMACompletion();
    VDP_setBGAAddress(0xC000u);
    VDP_clearPlane(BG_A,TRUE); /* BANK 1 destroyed the old C000 map. */
    VDP_waitDMACompletion();
    reload_cell_tiles();
    VDP_waitDMACompletion();
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_VRAM_READY),
               "restore original cell patterns and BG_A");
    restore_cell_palette();
    VDP_waitDMACompletion();
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_CRAM_READY),
               "restore cell palette");
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_MAP_READY),
               "restore 8x8 tilemap");
    m3c_expect(R46_M3_Commit(&owner),"commit original cell owner");
    m3c_expect(R46_M3_MayWrite(&owner,R46_M3_CELL),
               "cell mode not restored");
    VDP_setAutoInc(2);
    SYS_doVBlankProcess();
    VDP_setEnable(TRUE);
}
#endif
