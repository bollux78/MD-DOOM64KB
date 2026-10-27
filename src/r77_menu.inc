/* R77: real VDP shadow for low-priority stone, normal white text.
 * Included after HUD assets. Two stone phases, 96 composed glyphs per phase.
 * Text tiles carry an opaque, normal-intensity copy of the same shadowed
 * stone. This avoids the VDP's tile-wide priority brightening the background.
 * No highlight operator sprites; SH mode is restricted to the frozen menu. */
#define R77_MENU_BASE (HUDW_VRAM_BASE + HUDW_NTILES + 4u*HUDW_FACE_W)
#define R77_MENU_TILES (2u+2u*96u)
#if R77_MENU_BASE + R77_MENU_TILES > 1440u
#error R77 menu patterns overlap SGDK font
#endif
static const uint16_t r77_menu_pal[16]={
    0x000,0x000,0x222,0x444,0x666,0x888,0xCCC,0,0,0,0,0,0,0,0,0xEEE
};
/* At DAC input: shadow(2*k)=2*k == normal(k), for k=0..3. */
static uint32_t R77_StoneRow(uint16_t phase,uint16_t row,uint16_t shadow)
{
    static const uint8_t shade_code[4]={1,3,5,6};
    uint16_t id=hudw_bgmap[0][HUDW_HEALTH_C+1u+(phase&1u)];
    uint32_t source=hudw_tiles[id][row],result=0;
    for(uint16_t x=0;x<8u;x++){
        uint16_t shift=28u-4u*x;
        uint16_t w=hudw_pal[(source>>shift)&15u];
        uint16_t y=(299u*((w>>1)&7u)+587u*((w>>5)&7u)+114u*((w>>9)&7u)+500u)/1000u;
        uint16_t k=(y+1u)/2u;if(k>3u)k=3u;
        uint16_t c=shadow?shade_code[k]:(uint16_t)(k+1u);
        result|=(uint32_t)c<<shift;
    }
    return result;
}
static uint16_t R77_MenuWord(uint16_t x,uint8_t c)
{
    if(c<32u || c>127u)c=' ';
    return (uint16_t)(0x8000u+R77_MENU_BASE+2u+(x&1u)*96u+c-32u);
}
static void R77_MenuEnter(void)
{
    R20_StopVideo();VDP_waitDMACompletion();VDP_setEnable(FALSE);
    uint32_t tile[8],glyph[8];
    volatile uint32_t *ctrl=(volatile uint32_t*)0xC00004;
    volatile uint16_t *data=(volatile uint16_t*)0xC00000;
    for(uint16_t p=0;p<2u;p++){
        for(uint16_t y=0;y<8u;y++)tile[y]=R77_StoneRow(p,y,1);
        VDP_loadTileData(tile,(uint16_t)(R77_MENU_BASE+p),1,CPU);
    }
    for(uint16_t c=0;c<96u;c++){
        /* Read the actual loaded SGDK font; do not depend on SDK asset paths. */
        uint16_t sr=R22_Lock();VDP_setAutoInc(2);
        *ctrl=VDP_READ_VRAM_ADDR((uint32_t)(TILE_FONT_INDEX+c)*32u);
        for(uint16_t y=0;y<8u;y++){
            uint32_t hi=*data;glyph[y]=(hi<<16)|*data;
        }
        R22_Unlock(sr);
        for(uint16_t p=0;p<2u;p++){
            for(uint16_t y=0;y<8u;y++){
                uint32_t bg=R77_StoneRow(p,y,0),line=0;
                for(uint16_t x=0;x<8u;x++){
                    uint16_t shift=28u-x*4u;
                    uint32_t v=((glyph[y]>>shift)&15u)?15u:((bg>>shift)&15u);
                    line|=v<<shift;
                }
                tile[y]=line;
            }
            VDP_loadTileData(tile,(uint16_t)(R77_MENU_BASE+2u+p*96u+c),1,CPU);
        }
    }
    PAL_setColors(0,r77_menu_pal,16,CPU);
    uint16_t sr=R22_Lock();VDP_setAutoInc(2);
    for(uint16_t y=0;y<22u;y++){
        *ctrl=VDP_WRITE_VRAM_ADDR(VDP_BG_B+y*128u);
        for(uint16_t x=0;x<64u;x++)*data=(uint16_t)(R77_MENU_BASE+(x&1u));
    }
    VDP_setHorizontalScroll(BG_B,0);
    /* Window covers only the menu; HUD rows 22..25 retain high priority. */
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,22);
    VDP_setHilightShadow(TRUE);
    R22_Unlock(sr);VDP_setEnable(TRUE);
}
static void R77_MenuLeave(void)
{
    VDP_setHilightShadow(FALSE);
    R22_Palette((int8_t)r77_last_palette);VDP_waitDMACompletion();
    VDP_setHorizontalScroll(BG_B,r57_h32_active?-20:4);
    r57_hud_dirty=1;
}
