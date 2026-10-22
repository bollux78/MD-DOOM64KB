/* R51: first-person PISG weapon as Sega VDP hardware sprites.
 * Experimental subset: pistol ready/recoil, no muzzle flash or invisibility.
 * Other weapons/flash/fuzz retain proven software column renderer.
 * No heap allocations; 8 B of state and ROM-preconverted tile patterns.
 */
#if !defined(DOOM_R51_HW_WEAPON) || !defined(DOOM_R48_PAIR_V)
#error R51 hardware pistol sprites require Pair-V and explicit opt-in
#endif
#include "r51_weapon_assets.h"
#if R51_PISTOL_TILE_BASE!=16u || R51_PISTOL_TILE_LIMIT>256u
#error R51 hardware pistol tile atlas must fit in spare patterns 16..255
#endif

static int8_t r51_pending_asset=-1;
static int8_t r51_loaded_asset=-1;
static uint8_t r51_weapon_visible;
static int16_t r51_weapon_x,r51_weapon_y;

/* Called during R_DrawPSprite before the expensive column/raster work.
 * Return TRUE only for preconverted PISG frames; no WAD copy is needed. */
bool I_R51_WeaponSubmit(int16_t lump,int16_t phys_x,int16_t phys_y)
{
    const char __far *name=W_GetNameForNum(lump);
    for(uint16_t i=0;i<R51_WEAPON_ASSET_COUNT;i++){
        const char *candidate=r51_weapon_assets[i].name;
        uint8_t match=1;
        for(uint16_t c=0;c<8;c++)
            if(name[c]!=candidate[c]){match=0;break;}
        if(!match)continue;
        r51_pending_asset=(int8_t)i;
        r51_weapon_x=phys_x;
        r51_weapon_y=phys_y;
        return true;
    }
    return false; /* Continue in original software R_DrawVisSprite(). */
}

static void R51_WeaponHide(void)
{
    if(!r51_weapon_visible)return;
    /* Zero first SAT entry, link=0: no subsequent sprite is visible. */
    R20_StopVideo();
    uint16_t sr=R22_Lock();
    volatile uint32_t *ctrl=(volatile uint32_t*)0xC00004;
    volatile uint16_t *data=(volatile uint16_t*)0xC00000;
    VDP_setAutoInc(2);
    *ctrl=VDP_WRITE_VRAM_ADDR(0xF400);
    *data=0;*data=0;*data=0;*data=0;
    R22_Unlock(sr);
    r51_weapon_visible=0;
}

static void R51_WeaponInvalidate(void)
{
    R51_WeaponHide();
    r51_loaded_asset=-1;
    r51_pending_asset=-1;
}
static void R51_WeaponBeginFrame(void){r51_pending_asset=-1;}

static void R51_WeaponPresent(void)
{
    if(r51_pending_asset<0 || _g_gamestate!=GS_LEVEL || _g_menuactive){
        R51_WeaponHide();
        return;
    }
    const R51WeaponAsset *asset=&r51_weapon_assets[(uint8_t)r51_pending_asset];
    if(asset->tile_count>R51_PISTOL_TILE_LIMIT-R51_PISTOL_TILE_BASE ||
       asset->block_count>20){R51_WeaponHide();return;}
    R20_StopVideo();
    if(r51_loaded_asset!=r51_pending_asset){
        /* Art is prepacked in VDP column-major 8x8 tile order; upload
         * only when weapon frame changes, not on each player bob/tic. */
        VDP_loadTileData((const uint32_t*)asset->patterns,
                         R51_PISTOL_TILE_BASE,asset->tile_count,CPU);
        r51_loaded_asset=r51_pending_asset;
    }
    uint16_t sr=R22_Lock();
    volatile uint32_t *ctrl=(volatile uint32_t*)0xC00004;
    volatile uint16_t *data=(volatile uint16_t*)0xC00000;
    VDP_setAutoInc(2);
    *ctrl=VDP_WRITE_VRAM_ADDR(0xF400); /* Fixed Pair-V hardware SAT. */
    for(uint16_t i=0;i<asset->block_count;i++){
        const R51WeaponBlock *b=&asset->blocks[i];
        uint16_t y=(uint16_t)(r51_weapon_y+b->y+128)&0x1FFu;
        uint16_t x=(uint16_t)(r51_weapon_x+b->x+128)&0x1FFu;
        uint16_t size=(uint16_t)(((b->w-1u)<<2)|(b->h-1u));
        uint16_t link=(i+1u<asset->block_count)?(uint16_t)(i+1u):0u;
        *data=y;
        *data=(uint16_t)((size<<8)|link);
        *data=(uint16_t)(0xC000u+R51_PISTOL_TILE_BASE+b->tile_offset);
        *data=x;
    }
    R22_Unlock(sr);
    r51_weapon_visible=1;
}
