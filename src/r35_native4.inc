/* R35: render the exact same 320x224 Bayer8 pictures in pixel4 builds.
 * The 76x44 gameplay renderer uses both VRAM tile banks; pictures are
 * displayed ONLY outside gameplay. On reentry, the 4x4 tiles are rebuilt
 * by the regular renderer, avoiding a second framebuffer or decompressor.
 */
#if defined(DOOM_R30_NATIVE) && defined(DOOM_R35_ART_RAW)
#include "r30_static_manifest.h"
#if defined(DOOM_R47_PLANE_PAIR)
#define R35_FONT_TILE_LIMIT 1440
#else
#define R35_FONT_TILE_LIMIT 1696
#endif
#if (16 + R30_TITLE_TILES >= R35_FONT_TILE_LIMIT) || (16 + R30_INTER_TILES >= R35_FONT_TILE_LIMIT) || (16 + R30_FINAL_TILES >= R35_FONT_TILE_LIMIT)
#error R35 static picture would overwrite the SGDK font tiles
#endif
extern const u8 r30_title_pack[],r30_inter_pack[],r30_final_pack[];
extern const u16 r30_title_map[],r30_inter_map[],r30_final_map[];
extern const u16 r30_title_pal[],r30_inter_pal[],r30_final_pal[];
#if defined(DOOM_R78_ART)
extern const u16 r30_title_mapb[],r30_inter_mapb[];
#define R78_TITLE_MAPB r30_title_mapb
#define R78_INTER_MAPB r30_inter_mapb
#else
#define R78_TITLE_MAPB 0
#define R78_INTER_MAPB 0
#endif
typedef struct {
    const u8 *pixels;
    const u16 *map;
    const u16 *palette;
    u16 tile_count;
    const u16 *back_map; /* Optional opaque base; map is sparse foreground. */
} R35Native4;
static const R35Native4 r35_native4[3]={
    {r30_title_pack,r30_title_map,r30_title_pal,R30_TITLE_TILES,R78_TITLE_MAPB},
    {r30_inter_pack,r30_inter_map,r30_inter_pal,R30_INTER_TILES,R78_INTER_MAPB},
    {r30_final_pack,r30_final_map,r30_final_pal,R30_FINAL_TILES,0}
};
static int16_t r35_native_active=-1;
#if defined(DOOM_R50_STATIC_MENU)
/* Called by R40B's displaced-glyph restoration. Native tilemap is immutable
 * ROM data; no framebuffer duplication or new WRAM shadow required. */
static uint16_t R35_NativeMapWord(uint16_t x,uint16_t y)
{
    if(r35_native_active<0 || x>=40 || y>=28)return 0;
    return (uint16_t)(r35_native4[r35_native_active].map[y*40u+x]+16u);
}
#endif
static void R35_LeaveNative4(void)
{
    if(r35_native_active<0)return;
    R20_StopVideo();
#if defined(DOOM_R51_HW_WEAPON)
    /* Native art overwrites VRAM tiles 16..255. Invalidate the pistol
     * atlas now so the next gameplay presentation reloads it from ROM. */
    R51_WeaponInvalidate();
#endif
    VDP_setEnable(FALSE);
    VDP_clearPlane(BG_A,TRUE);
#if defined(DOOM_R47_PLANE_PAIR)
    /* Static art mirrored to B.  It must be erased on leave as well:
     * otherwise transparent parts of gameplay and the HUD show title art. */
    VDP_clearPlane(BG_B,TRUE);
#endif
    VDP_clearPlane(WINDOW,TRUE);
    VDP_waitDMACompletion();
    VDP_setWindowHPos(FALSE,0);
    VDP_setWindowVPos(FALSE,0);
    /* Picture load replaces the first 16 solid tiles. Restore them.
       Other dynamic bank tiles are refreshed by R22_UploadBack. */
    u16 sr=R22_Lock();
    volatile u32 *data=(volatile u32*)0xC00000;
    volatile u32 *ctrl=(volatile u32*)0xC00004;
    VDP_setAutoInc(2);
    *ctrl=VDP_WRITE_VRAM_ADDR(0);
    for(u16 c=0;c<16;c++)
    {
        u32 row=(u32)c*0x11111111UL;
        for(u16 y=0;y<8;y++)*data=row;
    }
    R22_Unlock(sr);
#if defined(DOOM_R47_PLANE_PAIR)
    /* Native art occupies the pair-pattern range. Restore all 256 immutable
     * pair patterns once before returning to gameplay. */
    R47_LoadPairTiles();
#if defined(DOOM_R48_PAIR_V)
    VDP_setVerticalScroll(BG_B,0);
    VDP_setHorizontalScroll(BG_B,4);
#else
    VDP_setVerticalScroll(BG_B,-4);
#endif
#endif
#if defined(DOOM_R56_DUAL_COLOR)
#if defined(DOOM_R59_COLOR_VIEW)
    /* R59 must restore the SELECTED CRAM alongside the selected Pair-V
     * patterns above. The historical A6 modes do not use CM6 colors. */
    PAL_setColors(0,R59_CURRENT.pal0[0],16,CPU);
    PAL_setColors(16,R59_CURRENT.pal1[0],16,CPU);
    r59_color_dirty=0; /* native exit rebuilt selected tiles and CRAM */
#else
    PAL_setColors(0,r56_pal0[0],16,CPU);
    PAL_setColors(16,r56_pal1[0],16,CPU);
#endif
#elif defined(DOOM_R52_AB)
    PAL_setColors(0,r52_pal0,16,CPU);
    PAL_setColors(16,r52_pal1,16,CPU);
#else
    PAL_setColors(0,r22_cram[0],16,CPU);
#endif
#if defined(DOOM_R51_HW_WEAPON)
    PAL_setColors(32,r51_weapon_pal2[0],16,CPU);
#endif
#if defined(DOOM_R49_COLORMIX)
    /* Native static pictures load all 64 CRAM entries. Restore PAL1's
     * additional 15 game shades before re-enabling raster gameplay. */
    PAL_setColors(16,r49_palette1,16,CPU);
    r49_gate_current=r49_mix_ok;
#if defined(DOOM_R49_COMPLUT)
    r49_compgate_current=r49_compgate;
#endif
#endif
    r22_newpal=100;
    r22_queued_pal=100;
    r22_overlay_dirty=0;
    r22_text_this_frame=0;
#if defined(DOOM_R47_PLANE_PAIR)
    /* Pair native-text occupancy masks alias the idle framebuffer. Restore
     * valid 0x0100 tile words before the renderer or VBlank DMA sees it. */
    R47_ClearPairBuffer();
#else
    R40B_ResetNativeText();
#endif
    r22_front=0;
    r22_ready=0;
    r35_native_active=-1;
    VDP_setEnable(TRUE);
}
static bool R35_DrawNative4(int16_t lump)
{
    static const char *const names[3]={"TITLEPIC","WIMAP0","HELP2"};
    static int16_t ids[3];
    static bool known=FALSE;
    if(!known)
    {
        for(u16 i=0;i<3;i++)ids[i]=W_GetNumForName(names[i]);
        known=TRUE;
    }
    for(u16 i=0;i<3;i++)
    {
        if(lump!=ids[i])continue;
        if(r35_native_active==(int16_t)i)return TRUE;
#if defined(DOOM_R51_HW_WEAPON)
        R51_WeaponInvalidate();
#endif
        const R35Native4 *picture=&r35_native4[i];
        R20_StopVideo();
        VDP_setEnable(FALSE);
        VDP_clearPlane(BG_A,TRUE);
#if defined(DOOM_R47_PLANE_PAIR)
        VDP_clearPlane(BG_B,TRUE);
        VDP_setVerticalScroll(BG_B,0);
#if defined(DOOM_R48_PAIR_V)
        VDP_setHorizontalScroll(BG_B,0);
#endif
#endif
        VDP_clearPlane(WINDOW,TRUE);
#if defined(DOOM_R50_STATIC_MENU)
        /* With text written directly into BG_A and restored from ROM, a
         * full-screen WINDOW would hide the 320x224 static background. */
        VDP_setWindowHPos(FALSE,0);
#else
        VDP_setWindowHPos(TRUE,0);
#endif
        VDP_setWindowVPos(FALSE,0);
        /* Tile data are 32B raw 4bpp, already converted with Bayer8.
           Every tile lives directly in ROM. Never call a codec here. */
        for(u16 t=0;t<picture->tile_count;t++)
            VDP_loadTileData((const u32*)(const void*)(picture->pixels+32UL*t),
                             16+t,1,CPU);
        u16 row[40];
        for(u16 y=0;y<28;y++)
        {
            for(u16 x=0;x<40;x++)row[x]=picture->map[y*40+x]+16;
            VDP_setTileMapDataRect(BG_A,row,0,y,40,1,40,CPU);
#if defined(DOOM_R47_PLANE_PAIR)
            if(picture->back_map)
                for(u16 x=0;x<40;x++)row[x]=picture->back_map[y*40+x]+16;
            /* Mirror the native picture on B so transparent WINDOW glyphs
             * reveal the complete static image, not odd scanline pairs.
             * R78 user art instead puts its opaque base in B and exact sparse
             * corrections in A. Native glyph retirement restores map A. */
            VDP_setTileMapDataRect(BG_B,row,0,y,40,1,40,CPU);
#endif
        }
        PAL_setColors(0,picture->palette,64,CPU);
        r22_newpal=100;
        r22_queued_pal=100;
        r22_overlay_dirty=0;
        R40B_ResetNativeText(); /* WINDOW is newly blank, so invalidate glyph shadow. */
        r35_native_active=(int16_t)i;
        VDP_setEnable(TRUE);
        return TRUE;
    }
    return FALSE;
}
#endif

#undef R35_FONT_TILE_LIMIT
#undef R78_TITLE_MAPB
#undef R78_INTER_MAPB

