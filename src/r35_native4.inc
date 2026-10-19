/* R35: render the exact same 320x224 Bayer8 pictures in pixel4 builds.
 * The 76x44 gameplay renderer uses both VRAM tile banks; pictures are
 * displayed ONLY outside gameplay. On reentry, the 4x4 tiles are rebuilt
 * by the regular renderer, avoiding a second framebuffer or decompressor.
 */
#if defined(DOOM_R30_NATIVE) && defined(DOOM_R35_ART_RAW)
#include "r30_static_manifest.h"
#if (16 + R30_TITLE_TILES >= 1696) || (16 + R30_INTER_TILES >= 1696) || (16 + R30_FINAL_TILES >= 1696)
#error R35 static picture would overwrite the SGDK font tiles
#endif
extern const u8 r30_title_pack[],r30_inter_pack[],r30_final_pack[];
extern const u16 r30_title_map[],r30_inter_map[],r30_final_map[];
extern const u16 r30_title_pal[],r30_inter_pal[],r30_final_pal[];
typedef struct {
    const u8 *pixels;
    const u16 *map;
    const u16 *palette;
    u16 tile_count;
} R35Native4;
static const R35Native4 r35_native4[3]={
    {r30_title_pack,r30_title_map,r30_title_pal,R30_TITLE_TILES},
    {r30_inter_pack,r30_inter_map,r30_inter_pal,R30_INTER_TILES},
    {r30_final_pack,r30_final_map,r30_final_pal,R30_FINAL_TILES}
};
static int16_t r35_native_active=-1;
static void R35_LeaveNative4(void)
{
    if(r35_native_active<0)return;
    R20_StopVideo();
    VDP_setEnable(FALSE);
    VDP_clearPlane(BG_A,TRUE);
    VDP_clearPlane(WINDOW,TRUE);
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
    PAL_setColors(0,r22_cram[0],16,CPU);
    r22_newpal=100;
    r22_queued_pal=100;
    r22_overlay_dirty=0;
    r22_text_this_frame=0;
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
        const R35Native4 *picture=&r35_native4[i];
        R20_StopVideo();
        VDP_setEnable(FALSE);
        VDP_clearPlane(BG_A,TRUE);
        VDP_clearPlane(WINDOW,TRUE);
        VDP_setWindowHPos(TRUE,0);
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
        }
        PAL_setColors(0,picture->palette,64,CPU);
        r22_newpal=100;
        r22_queued_pal=100;
        r22_overlay_dirty=0;
        r35_native_active=(int16_t)i;
        VDP_setEnable(TRUE);
        return TRUE;
    }
    return FALSE;
}
#endif
