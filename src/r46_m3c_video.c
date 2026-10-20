/* R46 M3C: 4-phase real VDP dual-pattern-bank diagnostic.
 * Two pattern banks (54..851 and 890..1687) are displayed in alternation.
 * BANK 1 OVERLAPS BG_B AT 0xC000 (NOT BG_A). In the established SGDK
 * 64x32 layout BG_A is already at 0xE000, so it MUST stay there.
 * Redirect BG_B to the same E000 map for the diagnostic, then restore
 * BG_B to C000 and clear it before handing control back to R39f.
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
#if defined(DOOM_R46_M3C_DIRECT_REGS)
    /* Diagnostic errors must not remain invisible behind display-off.
     * Fail visibly and leave R39f control build completely unchanged. */
    if(!ok) {
        VDP_setEnable(TRUE);
        PAL_setColor(0,0x00Eu);
        I_Error("R46 M3C R4B: %s",message);
    }
#else
    if(!ok)I_Error("R46 M3C: %s",message);
#endif
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
    /* 1688 patterns * 32 = 0xD300, below the SGDK font at 0xD400.
     * SGDK 64x32 keeps A at E000 and B at C000, unlike the old
     * assumption that triggered 'unexpected BG_A base' at boot.
     * Bank1 destroys C000 (BG_B), never the E000 BG_A map.
     * While testing, mirror BG_B onto BG_A's map so the scrolling
     * background cannot display corrupted bank1 pattern data as names. */
    m3c_expect(1688u*32u<=0xD400u && 0xE000u>1688u*32u,
               "VRAM layout overlap");
    m3c_expect(VDP_getBGAAddress()==0xE000u,"unexpected BG_A base");
    m3c_expect(VDP_getBGBAddress()==0xC000u,"unexpected BG_B base");
    /* Bank1 (0x6F40..0xD2FF) also intersects the 64x32 H40
     * WINDOW tilemap at D000..D2FF. Mirror its address to E000
     * alongside BG_A/B. Never clear the entire D000 Window on restore:
     * the 8x8 SGDK font starts at D400. */
    m3c_expect(VDP_getWindowAddress()==0xD000u,
               "unexpected WINDOW base");
    VDP_setEnable(FALSE);
    VDP_setAutoInc(2);
#if defined(DOOM_R46_M3C_DIRECT_REGS)
    /* Isolated experiment: keep SGDK cached maps_addr at C000.
     * BG_B 0xE000: VDP register 4 = 0x07.
     * Window 0xE000 H40: register 3 = 0x38.
     * This avoids SGDK implicit font reload/MEM_pack during remap. */
    volatile uint16_t *const vdp_ctrl=(volatile uint16_t*)VDP_CTRL_PORT;
    m3c_expect(VDP_MAPS_START==0xC000u && TILE_FONT_INDEX==1440u,
               "unexpected SGDK font/map base before raw remap");
    *vdp_ctrl=0x8407u;
    *vdp_ctrl=0x8338u;
    m3c_expect(VDP_getBGBAddress()==0xC000u &&
               VDP_getWindowAddress()==0xD000u,
               "SGDK address cache changed by raw register writes");
#else
    VDP_setBGBAddress(0xE000u);
    VDP_setWindowAddress(0xE000u);
    m3c_expect(VDP_getBGBAddress()==0xE000u &&
               VDP_getWindowAddress()==0xE000u,
               "BG_B / WINDOW diagnostic mirror");
#endif
    VDP_setTextPlane(BG_A);
    VDP_clearPlane(BG_A,TRUE);
    VDP_waitDMACompletion();
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_VRAM_READY),
               "safe BG_A/B diagnostic maps");
    PAL_setColors(0,r22_cram[0],16,CPU);
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_CRAM_READY),
               "pixel4 diagnostic palette");
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_MAP_READY),
               "clear relocated map");
    m3c_expect(R46_M3_Commit(&owner),"commit pixel4");
    m3c_expect(R46_M3_MayWrite(&owner,R46_M3_PIXEL4),
               "pixel4 owner unavailable");

    uint8_t *pixels=(uint8_t *)(void*)backing;
#if defined(DOOM_R46_M3C_STRESS)
    /* Stress experimental variant: repeat 4-color phases three times. */
    const uint16_t phases=12;
#else
    const uint16_t phases=4;
#endif
    for(uint16_t phase=0;phase<phases;phase++){
        const uint16_t bank=(uint16_t)(phase&1u);
        m3c_expect(R46_M3C_StageBank(&banks,bank),"stage hidden bank");
        m3c_expect(R46_M3C_BankWritable(&banks,bank),"visible bank hazard");
        m3c_expect(R46_M3C_MakePattern(pixels,1672,(uint16_t)(phase&3u)),
                   "phase pattern generation");
        /* Only the NOT currently visible bank receives tile patterns.
         * Starting phase 0 runs with display off; subsequent hidden-bank
         * uploads can run with the prior bank still visible. */
#if defined(DOOM_R46_M3C_SAFE_BLANK)
        /* Control experiment: keep the screen blank throughout the
         * large CPU tile upload, not only the 21-row map replacement.
         * This isolates display contention / timing as possible causes. */
        VDP_setEnable(FALSE);
        VDP_waitDMACompletion();
#endif
        m3c_upload_hidden_bank(&owner,&banks,pixels,bank);
        m3c_swap_map_while_blanked(&owner,&banks,pixels,bank);
        for(uint16_t frame=0;frame<45;frame++)SYS_doVBlankProcess();
    }

    /* The native bank1 spans tile index 928..1687, INCLUDING the
     * ORIGINAL SGDK glyph atlas when maps_addr=C000:
     * TILE_FONT_INDEX = (C000/32)-96 = 1440 (B400..BFFF).
     * Mirroring BG_B/Window changes maps_addr and SGDK attempts
     * automatic glyph reloads at transient locations. The R3 opt-in
     * proves whether an EXPLICIT post-restoration font reload repairs
     * the corrupted DEMO3 text that persists in both R2 variants.
     * Never assume that the font lives at D400 (index 1696).
     */
    /* Restore the R39f framebuffer owner and all overwritten VRAM. */
    m3c_expect(R46_M3_Request(&owner,R46_M3_CELL),"request 8x8");
    VDP_setEnable(FALSE);
    VDP_waitDMACompletion();
    m3c_expect(R46_M3_AckQuiesce(&owner,R46_M3_DMA_DRAINED),
               "drain pixel4 DMA");
    m3c_expect(R46_M3_AckQuiesce(&owner,R46_M3_IRQ_DISABLED),
               "retire pixel4 display");
    VDP_clearPlane(BG_A,TRUE); /* Clear pixel4 BG_A at E000. */
    VDP_waitDMACompletion();
#if defined(DOOM_R46_M3C_DIRECT_REGS)
    /* Restore the SAME safe ordering as the approved R3:
     * Window D000, clear damaged six rows, then BG_B C000.
     * Direct register writes avoid SGDK's implicit font heap updates. */
    *vdp_ctrl=0x8334u;
    VDP_clearTileMapRect(WINDOW,0,0,64,6);
    *vdp_ctrl=0x8406u;
#else
    VDP_setWindowAddress(0xD000u); /* Restore inactive H40 Window. */
    /* Clear only the 6 damaged 64-word Window rows at D000..D2FF.
     * DO NOT clear all 32 rows: D400..DFFF contains SGDK font. */
    VDP_clearTileMapRect(WINDOW,0,0,64,6);
    VDP_setBGBAddress(0xC000u); /* Restore original BG_B base. */
#endif
    VDP_clearPlane(BG_B,TRUE); /* Bank1 overwrote BG_B names at C000. */
    VDP_waitDMACompletion();
    m3c_expect(VDP_getBGAAddress()==0xE000u &&
               VDP_getBGBAddress()==0xC000u &&
               VDP_getWindowAddress()==0xD000u,
               "original BG_A/B addresses not restored");
    reload_cell_tiles();
    VDP_waitDMACompletion();
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_VRAM_READY),
               "restore original cell patterns and BG_A");
    restore_cell_palette();
    VDP_waitDMACompletion();
#if defined(DOOM_R46_M3C_FONT_RESTORE)
    /* Both plane names and the Window were already restored here.
     * SGDK's dynamic TILE_FONT_INDEX must now point to the ORIGINAL
     * B400 glyph atlas. Re-upload ALL 96 glyphs explicitly only in
     * the R3 diagnostic, checking the allocation/decode return code. */
    m3c_expect(VDP_MAPS_START==0xC000u &&
               TILE_FONT_INDEX==1440u,
               "original SGDK font base not restored");
    m3c_expect(VDP_loadDefaultFont(CPU),
               "default font decompress/reload failed");
    VDP_waitDMACompletion();
#endif
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_CRAM_READY),
               "restore cell palette");
    m3c_expect(R46_M3_AckReconfigure(&owner,R46_M3_MAP_READY),
               "restore 8x8 tilemap");
    m3c_expect(R46_M3_Commit(&owner),"commit original cell owner");
    m3c_expect(R46_M3_MayWrite(&owner,R46_M3_CELL),
               "cell mode not restored");
    VDP_setAutoInc(2);
    /* Explicitly drain SGDK queued DMA + actual hardware DMA before
     * allowing the normal R39f video producer to resume. Palette restore
     * is performed by an immediate CPU callback in the R2 diagnostic. */
    SYS_doVBlankProcess();
    VDP_waitDMACompletion();
    VDP_setEnable(TRUE);
}
#endif
