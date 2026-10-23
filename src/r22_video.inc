/* R22: independent 76x44 raster, packed4bpp in RAM; each sample is4x4.
 * Two hidden/front tile banks in VRAM. Expand by CPU into the hidden bank,
 * then flip only the tilemap during VBlank, keeping the XGM service alive.
 * No expanded framebuffer in work RAM and no cartridge SRAM required.
 * GPL-2.0-or-later. */
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "compiler.h"
#include "i_system.h"
#include "i_video.h"
#include "v_video.h"
#include "w_wad.h"
#include "globdata.h"
#include "r20_stackguard.h"
#include "r20_dma.h"
#include "r21_textscreen.h"
#include "r21_prof.h"
#include "r20_counters.h"
#include "r22_pixel4.h"
#include "r57_viewport.h"
#if defined(DOOM_R43_GRAY_CRT)
#include "r43_gray_palette.h" /* 4x4 CRAM/LUT only; Bayer8 still unchanged. */
#else
#include "r22_palette.h"
#endif
#include "r22_maps.h"
#if defined(DOOM_R49_COLORMIX) || defined(DOOM_R49_COMPLUT)
#include "r49_colormix_tables.h"
#endif
#if defined(DOOM_R55_FLAT_SAFE) && (!defined(DOOM_R52_AB) || !defined(DOOM_R47_FLAT_HOIST))
#error R55 Werk requires R52 AB and flat hoist
#endif
#if defined(DOOM_R52_AB)
#include "r52_ab_tables.h"
#if defined(DOOM_R56_DUAL_COLOR)
#include "r56_tables.h"
#if defined(DOOM_R53_MICRO) || defined(DOOM_R55_FLAT_SAFE)
#error R56 has its own Flat-Safe maps and dual-color patterns
#endif
#if (R22_PAIR_TILE_BASE+512u > 1440u)
#error R56 dual color patterns collide with SGDK font
#endif
#endif
#if defined(DOOM_R55_FLAT_SAFE) && !defined(R55_FLAT_TABLES_VERSION)
#error R55 requires validated Werk snapshot tables
#endif
#if defined(DOOM_R53_MICRO)
#include "r53_micro_tables.h"
#if (DOOM_R53_MICRO != 25) && (DOOM_R53_MICRO != 50)
#error R53 micro ratio must be 25 or 50
#endif
#if R22_PAIR_TILE_BASE + 512 > 1440
#error R53 pattern banks collide with font
#endif
#endif
#if !defined(DOOM_R48_PAIR_V) || !defined(DOOM_R48_V_FAST) || defined(DOOM_R49_COLORMIX) || defined(DOOM_R49_COMPLUT)
#error R52 AB requires Pair-V Fast without R49 mix/composed LUT
#endif
#if defined(DOOM_R52_CPLUT)
extern const uint8_t *fullcolormap;
static inline const uint8_t *R52_LUT(const uint8_t *colormap,uint16_t parity)
{
    if(!colormap)return 0;
    uint32_t diff=(uint32_t)((uintptr_t)colormap-(uintptr_t)fullcolormap);
    if(diff>=R52_COLORMAP_BYTES || (diff&255u)!=0u)return 0;
    #if defined(DOOM_R56_DUAL_COLOR)
    return (parity?r56_comp_odd[0]:r56_comp_even[0])+diff;
#else
    return (parity?r52_comp_odd:r52_comp_even)+diff;
#endif
}
#endif
#endif
#if defined(DOOM_R49_COLORMIX) && (!defined(DOOM_R48_PAIR_V) || !defined(DOOM_R48_V_FAST))
#error R49 ColorMix requires Pair-V Fast
#endif
#if defined(DOOM_R49_COLORMIX) && (R22_PAIR_TILE_BASE + 1024 >= 1440)
#error R49 ColorMix pattern tiles overlap SGDK font
#endif
#if defined(DOOM_R49_COLORMIX)
#if defined(DOOM_R49_MIX_75A)
#define r49_mix_a r49_mix_a_75a
#define r49_mix_b r49_mix_b_75a
#define r49_mix_ok r49_mix_ok_75a
#define r49_compgate r49_compgate_75a
#elif defined(DOOM_R49_MIX_75B)
#define r49_mix_a r49_mix_a_75b
#define r49_mix_b r49_mix_b_75b
#define r49_mix_ok r49_mix_ok_75b
#define r49_compgate r49_compgate_75b
#else
#define r49_mix_a r49_mix_a_50
#define r49_mix_b r49_mix_b_50
#define r49_mix_ok r49_mix_ok_50
#define r49_compgate r49_compgate_50
#endif
/* Two ROM pointers (8 B WRAM) select the current 14-palette lighting gate.
 * No per-pixel floating point, RGB arithmetic, or external scratch bitmap. */
static const uint8_t *r49_gate_current=r49_mix_ok;
#if defined(DOOM_R49_COMPLUT)
static const uint8_t *r49_compgate_current=r49_compgate;
#endif
#endif

#if defined(DOOM_R22_PAIR_LUT)
#include "r22_pair_lut.h"
#endif
#if defined(DOOM_BUILD_VARIANT)
#include "doom_build_identity.h"
#endif
#if VIEWWINDOWWIDTH != R22_W || VIEWWINDOWHEIGHT != R22_H
#error PX4 requires76x44 independent samples
#endif
#if !defined(DOOM_R20_VBLANK_VIDEO) || !defined(DOOM_R21_NO_VDP_INIT)
#error PX4 requires the VBlank callback and heap-safe result screens
#endif
#if defined(DOOM_R21_FRAME_HASH) || defined(DOOM_R20_REG_COLUMNS) || defined(DOOM_R20_FLAT_INLINE)
#error Tile-word kernels and the old tilemap hash are incompatible with packed4bpp
#endif
extern const int16_t CENTERY;
extern volatile uint32_t _g_vblankCount;
extern void R22_InitOpenings(void);
void *R22_Alloc(uint16_t n) { return MEM_alloc(n); }
static struct {uint32_t before;uint8_t pixels[R22_FB_BYTES];uint32_t after;} r22_fb;
static volatile uint16_t r22_ready;
/* R48 P0: count submitted/visible raster work, not 68000 cycles.
 * Instrumented PERF must not be used as a speed baseline.
 * Exactly 8 longs = 32 B of extra BSS; respect the Pair boot guard. */
#if defined(DOOM_R48_P0_PROFILE)
#if !defined(TIMEDEMO)
#error R48 P0 is a timedemo-only diagnostic
#endif
enum {
    R48_WALL_PIXELS, R48_FLAT_PIXELS, R48_SPRITE_PIXELS,
    R48_WALL_CALLS, R48_FLAT_CALLS, R48_SPRITE_CALLS,
    R48_WAIT_CALLS, R48_WAIT_SPINS, R48_STATS_N
};
static uint32_t r48_prof[R48_STATS_N];
#define R48_COUNT(field,n) do { if(bench_active) r48_prof[(field)]+=(uint32_t)(n); } while(0)
#else
#define R48_COUNT(field,n) ((void)0)
#endif
static volatile uint16_t r22_front;
static uint16_t r22_next_bank;
static uint32_t r22_queued;
static uint8_t r22_overlay_dirty,r22_text_this_frame;
#if defined(DOOM_R57_CROP16)
static uint8_t r57_queued_crop;
static uint8_t r57_was_level;
#if defined(DOOM_R57_SIZE_MENU)
uint8_t r57_crop_enabled=1;
void R57_SetCrop(uint8_t enabled){
    R20_StopVideo();r57_crop_enabled=(enabled!=0);r57_was_level=0;
}
#endif
#if defined(DOOM_R57_NARROW256)
static uint8_t r57_hud_dirty;
#endif
#if defined(DOOM_R57_H32)
static uint8_t r57_h32_active;
static void R57_VideoMode(void){
    uint8_t desired=(_g_gamestate==GS_LEVEL && (!_g_menuactive || _g_demoplayback));
    if(desired==r57_h32_active)return;
    VDP_setEnable(FALSE);VDP_waitDMACompletion();
    if(desired)VDP_setScreenWidth256();else VDP_setScreenWidth320();
    VDP_clearPlane(BG_A,TRUE);VDP_clearPlane(BG_B,TRUE);VDP_clearPlane(WINDOW,TRUE);
    VDP_waitDMACompletion();
    VDP_setHorizontalScroll(BG_A,desired?-24:0);
    VDP_setHorizontalScroll(BG_B,desired?-20:4);
    r57_h32_active=desired;r57_hud_dirty=1;r57_was_level=0;r22_overlay_dirty=0;
    VDP_setEnable(TRUE);
}
#endif

#endif
/* R40b: No additional WRAM.  The 38x21 4x4 VDP tilemap is used only
 * during raster gameplay, never while a native 320x224 static picture is
 * active.  Reuse its first 210 bytes as two 105-byte occupancy masks to
 * retain and prune WINDOW glyphs without a per-frame clear.
 * R35_LeaveNative4 invalidates these masks BEFORE gameplay rebuilds map. */
#define R40B_TEXT_W 38
#define R40B_TEXT_H 22
#define R40B_TEXT_N (R40B_TEXT_W*R40B_TEXT_H)
#define R40B_OCC_BYTES ((R40B_TEXT_N+7)/8)
#if !defined(DOOM_R22_SOLID_TILES)
#error R40b native text reuses r22_map and requires SOLID_TILES
#endif
/* One pending map only; BeginFrame/FinishUpdate wait before reusing it. */
#if defined(DOOM_R47_PLANE_PAIR)
/* Pair gameplay does not use the framebuffer while R35 native static art is
 * active. Reuse its first 210 bytes for the two native-text occupancy masks,
 * avoiding a separate boot-time WRAM object. R35_LeaveNative4 rebuilds valid
 * Pair tile words before gameplay resumes. */
#define r40b_native_prev (r22_fb.pixels)
#define r40b_native_seen (r22_fb.pixels+R40B_OCC_BYTES)
#else
static uint16_t r22_map[38*21] __attribute__((aligned(2)));
#define r40b_native_prev ((uint8_t*)(void*)r22_map)
#define r40b_native_seen (((uint8_t*)(void*)r22_map)+R40B_OCC_BYTES)
#endif
static void R40B_ResetNativeText(void)
{
    memset(r40b_native_prev,0,R40B_OCC_BYTES);
    memset(r40b_native_seen,0,R40B_OCC_BYTES);
}
static inline uint16_t R22_Lock(void){uint16_t sr;__asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr":"=d"(sr)::"cc","memory");return sr;}
static inline void R22_Unlock(uint16_t sr){__asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");}
#if defined(DOOM_R51_HW_WEAPON)
#include "r51_weapon_hw.inc"
#endif
/* SDK text helpers use a 256-byte stack array. Write bounded glyphs directly,
   with exclusive ownership of the VDP address/data ports for the whole string. */
#if defined(DOOM_R57_CROP16)
/* Clear only excluded tiles when entering a cropped level. Normal native
 * transitions already clear both planes. Never clear the HUD or FPS row. */
static void R57_ClearBorder(void){
    uint16_t sr=R22_Lock();
    volatile uint32_t *ctrl=(volatile uint32_t*)0xC00004;
    volatile uint16_t *data=(volatile uint16_t*)0xC00000;
    VDP_setAutoInc(2);
    for(uint16_t plane=0;plane<2;plane++){
        uint16_t base=plane?VDP_BG_B:VDP_BG_A;
        for(uint16_t y=1;y<22;y++){
            *ctrl=VDP_WRITE_VRAM_ADDR(base+y*128);
            for(uint16_t x=0;x<38;x++){
                if(y<R57_TILE_YMIN || y>=R57_TILE_YEND ||
                   x<R57_TILE_XMIN || x>=R57_TILE_XEND)*data=0;
                else *ctrl=VDP_WRITE_VRAM_ADDR(base+y*128+(x+1)*2);
            }
        }
    }
    R22_Unlock(sr);
}
#endif
static void R22_DrawText(uint16_t plane,const char *s,uint16_t x,uint16_t y){
#if defined(DOOM_R57_H32)
    /* Gameplay planes scroll -24px. Text coordinates remain screen-relative. */
    if(r57_h32_active){if(x>=32)return;x+=3;}
#endif
    if(x>=38 || y>=28)return;
    R20_StopVideo();
    uint16_t sr=R22_Lock();
    volatile uint32_t *ctrl=(volatile uint32_t*)0xC00004;
    volatile uint16_t *data=(volatile uint16_t*)0xC00000;
    VDP_setAutoInc(2);*ctrl=VDP_WRITE_VRAM_ADDR(plane+y*128+x*2);
    while(*s && x++<38){uint8_t c=(uint8_t)*s++;if(c<32 || c>127)c=' ';*data=0x8000u+(uint16_t)TILE_FONT_INDEX+c-32;}
    R22_Unlock(sr);
}
static void R22_ClearOverlay(void){
    R20_StopVideo();
    uint16_t sr=R22_Lock();
    /* Only rows0..21: never touch the aliased SAT/HScroll at FC00. */
    VDP_clearTileMap(VDP_WINDOW,0,64*22,TRUE);
#if defined(DOOM_R47_PLANE_PAIR)
    /* WINDOW replaces plane A. Keep plane B black while a gameplay menu is
     * open so transparent glyph pixels do not expose odd-only 4x4 rows. */
    VDP_clearTileMap(VDP_BG_B,0,64*22,TRUE);
#endif
    /* R40a: menu/intermission glyphs are written directly after this clear.
     * A pending DMA fill could otherwise overwrite freshly drawn characters.
     * Wait for the fill before subsequent CPU VRAM writes. */
    VDP_waitDMACompletion();
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,0);
    VDP_setAutoInc(2);R22_Unlock(sr);r22_overlay_dirty=0;
}
/* R40b: Write current text without blanking the WINDOW first, tracking
 * the positions occupied this frame. Repeated glyph writes do not cause
 * visible blinking; a transparent tile is written only for retired glyphs. */
#if defined(DOOM_R50_STATIC_MENU)
/* Native art is installed later by r35_native4.inc. Recreate only the
 * original map words displaced by glyphs, without allocating a second
 * 320x224 framebuffer or using the full-screen Window plane. */
static uint16_t R35_NativeMapWord(uint16_t x,uint16_t y);
#endif
static void R40B_DrawNativeText(int16_t x,int16_t y,const char *s)
{
    if(x<0||x>=R40B_TEXT_W||y<0||y>=R40B_TEXT_H)return;
    if(!r22_text_this_frame){
#if !defined(DOOM_R50_STATIC_MENU)
        /* Original R40b full-screen Window path; blacks out native art. */
        R20_StopVideo();
        uint16_t sr=R22_Lock();
        VDP_setWindowHPos(TRUE,0);
        VDP_setWindowVPos(FALSE,0);
        R22_Unlock(sr);
#endif
        r22_text_this_frame=1;
    }
    r22_overlay_dirty=1;
    int16_t col=x;
    const char *scan=s;
    while(*scan && col<R40B_TEXT_W){
        uint16_t i=(uint16_t)(y*R40B_TEXT_W+col);
        r40b_native_seen[i>>3]|=(uint8_t)(1u<<(i&7));
        scan++; col++;
    }
#if defined(DOOM_R50_STATIC_MENU)
    /* Priority text directly in BG_A, over intact full-screen native art
     * in BG_B. WINDOW stays hidden, preserving all 28 picture rows. */
    R22_DrawText(VDP_BG_A,s,(uint16_t)x,(uint16_t)y);
#else
    R22_DrawText(VDP_WINDOW,s,(uint16_t)x,(uint16_t)y);
#endif
}
static void R40B_PruneNativeText(void)
{
    uint16_t stale=0;
    for(uint16_t i=0;i<R40B_OCC_BYTES;i++){
        if(r40b_native_prev[i] & (uint8_t)~r40b_native_seen[i]){
            stale=1;break;
        }
    }
    if(stale){
        R20_StopVideo();
        uint16_t sr=R22_Lock();
        volatile uint32_t *ctrl=(volatile uint32_t*)0xC00004;
        volatile uint16_t *data=(volatile uint16_t*)0xC00000;
        VDP_setAutoInc(2);
        for(uint16_t y=0;y<R40B_TEXT_H;y++){
            uint16_t run=0;
            for(uint16_t x=0;x<R40B_TEXT_W;x++){
                uint16_t i=(uint16_t)(y*R40B_TEXT_W+x);
                uint8_t bit=(uint8_t)(1u<<(i&7));
                if((r40b_native_prev[i>>3]&bit) &&
                   !(r40b_native_seen[i>>3]&bit)){
                    if(!run)*ctrl=VDP_WRITE_VRAM_ADDR(
#if defined(DOOM_R50_STATIC_MENU)
                        VDP_BG_A+
#else
                        VDP_WINDOW+
#endif
                        y*128u+x*2u);
#if defined(DOOM_R50_STATIC_MENU)
                    /* Restore this glyph's exact title/intermission tile.
                     * Native art map is immutable ROM, so no RAM shadow. */
                    *data=R35_NativeMapWord(x,y);
#else
                    *data=0; /* Transparent WINDOW cell shows native art. */
#endif
                    run=1;
                }else run=0;
            }
        }
        R22_Unlock(sr);
    }
    memcpy(r40b_native_prev,r40b_native_seen,R40B_OCC_BYTES);
}

static int8_t r22_newpal=100,r22_queued_pal=100;
#define R22_GUARD 0x2244AA55u
/* Reuse the established timedemo and diagnostics, not the old raster. */
#if defined(DOOM_R21_NO_VDP_INIT) || defined(DOOM_R21_HEAP_PROBE)
volatile uint16_t r21_heap_at_end_free, r21_heap_at_end_largest;
void I_R21_ProbeHeap(void)
{
    r21_heap_at_end_free = MEM_getFree();
    r21_heap_at_end_largest = MEM_getLargestFreeBlock();
}
#endif
#if defined(DOOM_R21_NO_VDP_INIT)
void I_R21_TextScreen(void)
{
    /* Keep the boot VDP setup (H40, 64x32 planes, font tiles, Doom CRAM).
       Only stop pending DMA and blank both planes; DMA fill needs no heap. */
    VDP_waitDMACompletion();
    VDP_setHInterrupt(FALSE);
    VDP_clearPlane(BG_A, TRUE);
#if defined(DOOM_R47_PLANE_PAIR)
    /* Pair A/B name tables contain independent video samples.  Erase B
     * too, otherwise the PERF result screen retains raster stripes. */
    VDP_clearPlane(BG_B, TRUE);
#endif
    VDP_clearPlane(WINDOW, TRUE);
    VDP_waitDMACompletion();
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,0);
    VDP_setTextPlane(BG_A);
    VDP_setTextPriority(TRUE);
}
#endif


#include "r22_benchmark.inc"

/* Optional ROM-only composed colormap. If a caller passes a map outside
 * the WAD's ordinary COLORMAP lump, fall back to the original two lookups.
 * Never read outside a known 256-byte table. */
#if defined(DOOM_R49_COMPLUT)
extern const uint8_t *fullcolormap;
static inline const uint8_t *R49_MapLUT(const uint8_t *colormap)
{
    if(!colormap)return r22_color;
    uint32_t diff=(uint32_t)((uintptr_t)colormap-(uintptr_t)fullcolormap);
    return diff<R49_COLORMAP_BYTES ? r49_compmap+diff : 0;
}
#endif
#if defined(DOOM_R49_COLORMIX) || defined(DOOM_R49_COMPLUT)
static inline uint8_t R49_MapSample(uint8_t sample,const uint8_t *colormap,
                                   const uint8_t *fast,uint8_t *gate)
{
#if defined(DOOM_R49_COMPLUT)
    if(fast){
#if defined(DOOM_R49_COLORMIX)
        /* fast points either to r22_color or the composed COLORMAP slice. */
        if(colormap){
            uint32_t off=(uint32_t)(fast-r49_compmap);
            *gate=r49_compgate_current[off+sample];
        }else *gate=r49_gate_current[sample];
#else
        *gate=0;
#endif
        return fast[sample];
    }
#else
    (void)fast;
#endif
    if(colormap)sample=colormap[sample];
#if defined(DOOM_R49_COLORMIX)
    *gate=r49_gate_current[sample];
#else
    *gate=0;
#endif
    return r22_color[sample];
}
#endif

static inline void R22_Plot(int16_t x,int16_t y,uint8_t c) {
    if((uint16_t)x>=R22_W || (uint16_t)y>=R22_H)return;
    /* Same8px top/left safety border as the38x22 reference. */
#if defined(DOOM_R57_CROP16)
    if(_g_gamestate==GS_LEVEL && (R57_CROP_ACTIVE ?
       (x<R57_XMIN || x>=R57_XEND || y<R57_YMIN || y>=R57_YEND) :
       (x<2 || y<2)))return;
#else
    if(_g_gamestate==GS_LEVEL && (x<2 || y<2))return;
#endif
    R22_Put(r22_fb.pixels,(uint16_t)x,(uint16_t)y,c);
}
void R_DrawColumnSprite(const draw_column_vars_t *v) {
    const uint8_t *r52map=r22_color;
#if defined(DOOM_R56_DUAL_COLOR)
    r52map=(v->x&1u)?r56_wall_odd:r56_wall_even;
#elif defined(DOOM_R52_AB)
    r52map=(v->x&1u)?r52_odd:r52_even;
#endif
#if defined(DOOM_R47_SPRITE_HOIST)
    /* R47: same exact clipping/stride hoist as flats, while retaining the
     * sprite read-modify-write required to preserve the neighbouring nibble. */
    int16_t x=v->x, y0=v->yl, y1=v->yh;
    if(y1<y0 || (uint16_t)x>=R22_W)return;
#if defined(DOOM_R57_CROP16)
    int16_t border=(_g_gamestate==GS_LEVEL)?(R57_CROP_ACTIVE?R57_YMIN:2):0;
    if((_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE) && x>=R57_XEND)return;
    if((_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE) && y1>=R57_YEND)y1=R57_YEND-1;
#else
    int16_t border=(_g_gamestate==GS_LEVEL)?2:0;
#endif
    if(x<border)return;
    int16_t first=y0;
    if(first<border)first=border;
    if(first<0)first=0;
    if(y1>=R22_H)y1=R22_H-1;
    if(first>y1)return;
    R48_COUNT(R48_SPRITE_CALLS,1);
    R48_COUNT(R48_SPRITE_PIXELS,(uint16_t)(y1-first+1));
    uint16_t frac=(uint16_t)((v->texturemid>>7)+(y0-CENTERY)*v->fracstep);
    frac=(uint16_t)(frac+(uint16_t)((uint32_t)(uint16_t)(first-y0)*(uint32_t)v->fracstep));
    const uint16_t step=v->fracstep;
    const uint8_t *source=v->source,*colormap=v->colormap;
#if defined(DOOM_R52_CPLUT)
    const uint8_t *r52fast=R52_LUT(colormap,(uint16_t)(x&1u));
    if(r52fast){r52map=r52fast;colormap=0;}
#endif
    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)first);
    uint16_t n=(uint16_t)(y1-first);
#if defined(DOOM_R48_PAIR_V)
    uint16_t count=(uint16_t)(n+1u);
#if defined(DOOM_R49_COLORMIX) || defined(DOOM_R49_COMPLUT)
#if defined(DOOM_R49_COMPLUT)
    const uint8_t *fast=R49_MapLUT(colormap);
#else
    const uint8_t *fast=0;
#endif
    if((first&1u) && count){
        uint8_t gate=0;
        uint8_t c=R49_MapSample(source[frac>>9],colormap,fast,&gate);
        *dst=(uint8_t)((*dst&0xf0u)|c);
#if defined(DOOM_R49_COLORMIX)
        R49_WriteMixFlag(dst,first,gate);
#endif
        dst+=152; frac=(uint16_t)(frac+step); --count;
    }
    while(count>=2){
        uint8_t ga=0,gb=0;
        uint8_t a=R49_MapSample(source[frac>>9],colormap,fast,&ga);
        frac=(uint16_t)(frac+step);
        uint8_t b=R49_MapSample(source[frac>>9],colormap,fast,&gb);
        frac=(uint16_t)(frac+step);
        *dst=(uint8_t)((a<<4)|(b&15u));
#if defined(DOOM_R49_COLORMIX)
        dst[-1]=R49_TileAttr((uint8_t)((ga?1u:0u)|(gb?2u:0u)));
#endif
        dst+=152; count-=2;
    }
    if(count){
        uint8_t gate=0;
        uint8_t c=R49_MapSample(source[frac>>9],colormap,fast,&gate);
        *dst=(uint8_t)((*dst&0x0fu)|(c<<4));
#if defined(DOOM_R49_COLORMIX)
        R49_WriteMixFlag(dst,0,gate);
#endif
    }
#else
    uint16_t odd=(uint16_t)(first&1);
    if(odd && count) {
        uint8_t ci=source[frac>>9]; if(colormap)ci=colormap[ci];
        *dst=(uint8_t)((*dst&0xf0u)|(r52map[ci]&15u));
        dst+=152; frac=(uint16_t)(frac+step); --count;
    }
#if defined(DOOM_R48_V_FAST)
    while(count>=2) {
        uint8_t a=source[frac>>9]; if(colormap)a=colormap[a];
        frac=(uint16_t)(frac+step);
        uint8_t b=source[frac>>9]; if(colormap)b=colormap[b];
        frac=(uint16_t)(frac+step);
        *dst=(uint8_t)((r52map[a]<<4)|(r52map[b]&15u));
        dst+=152; count-=2;
    }
#else
    while(count>=2) {
        uint8_t ci=source[frac>>9]; if(colormap)ci=colormap[ci];
        *dst=(uint8_t)((*dst&0x0fu)|((r52map[ci]&15u)<<4));
        frac=(uint16_t)(frac+step);
        ci=source[frac>>9]; if(colormap)ci=colormap[ci];
        *dst=(uint8_t)((*dst&0xf0u)|(r52map[ci]&15u));
        frac=(uint16_t)(frac+step);
        dst+=152; count-=2;
    }
#endif
    if(count) {
        uint8_t ci=source[frac>>9]; if(colormap)ci=colormap[ci];
        *dst=(uint8_t)((*dst&0x0fu)|((r52map[ci]&15u)<<4));
    }
#endif /* R49 V optimized path */
#else
    if(x&1){
        do{
            uint8_t ci=source[frac>>9];if(colormap)ci=colormap[ci];
            *dst=(uint8_t)((*dst&0xf0u)|(r52map[ci]&15u));
            dst+=R22_PITCH;frac=(uint16_t)(frac+step);
        }while(n--);
    }else{
        do{
            uint8_t ci=source[frac>>9];if(colormap)ci=colormap[ci];
            *dst=(uint8_t)((*dst&0x0fu)|((r52map[ci]&15u)<<4));
            dst+=R22_PITCH;frac=(uint16_t)(frac+step);
        }while(n--);
    }
#endif /* Pair-V column renderer */
#else
    int16_t n=v->yh-v->yl+1;if(n<=0)return;
    uint16_t frac=(uint16_t)((v->texturemid>>7)+(v->yl-CENTERY)*v->fracstep);
    for(int16_t y=v->yl;y<=v->yh;y++) {
        uint8_t c=v->source[frac>>9];
        if(v->colormap)c=v->colormap[c];
        R22_Plot(v->x,y,r52map[c]);frac+=v->fracstep;
    }
#endif
}
/* R42 Q2: packed-4bpp wall-only specialization. This remains independent
 * of the R20 8x8 tile-word assembly kernels. Preserve the original sprite,
 * fuzz, and flat paths, where overdrawing an existing pixel is essential.
 *
 * Clip x/y once instead of calling R22_Plot for each drawn texel. The
 * 16-bit texture accumulator is advanced for skipped top rows to maintain
 * exact original sampling. Even x owns the high nibble; odd x owns low.
 * Both variants read-modify-write to preserve the neighbor pixel. */
#if defined(DOOM_R42_WALL_HOIST) || defined(DOOM_R42_WALL_ASM)
static void R42_DrawPackedWall(const draw_column_vars_t *v)
{
    const uint8_t *r52map=r22_color;
#if defined(DOOM_R56_DUAL_COLOR)
    r52map=(v->x&1u)?r56_wall_odd:r56_wall_even;
#elif defined(DOOM_R52_AB)
    r52map=(v->x&1u)?r52_odd:r52_even;
#endif
    int16_t x=v->x, y0=v->yl, y1=v->yh;
    if(y1<y0 || (uint16_t)x>=R22_W) return;
#if defined(DOOM_R57_CROP16)
    int16_t border=(_g_gamestate==GS_LEVEL)?(R57_CROP_ACTIVE?R57_YMIN:2):0;
    if((_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE) && x>=R57_XEND)return;
    if((_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE) && y1>=R57_YEND)y1=R57_YEND-1;
#else
    int16_t border=(_g_gamestate==GS_LEVEL)?2:0;
#endif
    if(x<border) return;
    int16_t first=y0;
    if(first<border) first=border;
    if(y1>=R22_H) y1=R22_H-1;
    if(first>y1) return;
    R48_COUNT(R48_WALL_CALLS,1);
    R48_COUNT(R48_WALL_PIXELS,(uint16_t)(y1-first+1));
    uint16_t f=(uint16_t)((v->texturemid>>7)+(y0-CENTERY)*v->fracstep);
    f=(uint16_t)(f+(uint16_t)((uint32_t)(uint16_t)(first-y0)*(uint32_t)v->fracstep));
    const uint16_t step=v->fracstep;
    const uint8_t *source=v->source, *colormap=v->colormap;
#if defined(DOOM_R52_CPLUT)
    const uint8_t *r52fast=R52_LUT(colormap,(uint16_t)(x&1u));
    if(r52fast){r52map=r52fast;colormap=0;}
#endif
    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)first);
    int16_t remaining=(int16_t)(y1-first+1);
#if defined(DOOM_R48_PAIR_V)
    uint16_t count=(uint16_t)(remaining);
#if defined(DOOM_R49_COLORMIX) || defined(DOOM_R49_COMPLUT)
#if defined(DOOM_R49_COMPLUT)
    const uint8_t *fast=R49_MapLUT(colormap);
#else
    const uint8_t *fast=0;
#endif
    if((first&1u) && count){
        uint8_t gate=0;
        uint8_t c=R49_MapSample(source[f>>9],colormap,fast,&gate);
        *dst=(uint8_t)((*dst&0xf0u)|c);
#if defined(DOOM_R49_COLORMIX)
        R49_WriteMixFlag(dst,first,gate);
#endif
        dst+=152; f=(uint16_t)(f+step); --count;
    }
    while(count>=2){
        uint8_t ga=0,gb=0;
        uint8_t a=R49_MapSample(source[f>>9],colormap,fast,&ga);
        f=(uint16_t)(f+step);
        uint8_t b=R49_MapSample(source[f>>9],colormap,fast,&gb);
        f=(uint16_t)(f+step);
        *dst=(uint8_t)((a<<4)|(b&15u));
#if defined(DOOM_R49_COLORMIX)
        dst[-1]=R49_TileAttr((uint8_t)((ga?1u:0u)|(gb?2u:0u)));
#endif
        dst+=152; count-=2;
    }
    if(count){
        uint8_t gate=0;
        uint8_t c=R49_MapSample(source[f>>9],colormap,fast,&gate);
        *dst=(uint8_t)((*dst&0x0fu)|(c<<4));
#if defined(DOOM_R49_COLORMIX)
        R49_WriteMixFlag(dst,0,gate);
#endif
    }
#else
    if((first&1) && count) {
        uint8_t ci=source[f>>9]; if(colormap)ci=colormap[ci];
        *dst=(uint8_t)((*dst&0xf0u)|(r52map[ci]&15u));
        dst+=152; f=(uint16_t)(f+step); --count;
    }
#if defined(DOOM_R48_V_FAST)
    while(count>=2) {
        uint8_t a=source[f>>9]; if(colormap)a=colormap[a];
        f=(uint16_t)(f+step);
        uint8_t b=source[f>>9]; if(colormap)b=colormap[b];
        f=(uint16_t)(f+step);
        *dst=(uint8_t)((r52map[a]<<4)|(r52map[b]&15u));
        dst+=152; count-=2;
    }
#else
    while(count>=2) {
        uint8_t a=source[f>>9]; if(colormap)a=colormap[a];
        f=(uint16_t)(f+step);
        *dst=(uint8_t)((*dst&0x0fu)|((r52map[a]&15u)<<4));
        uint8_t b=source[f>>9]; if(colormap)b=colormap[b];
        f=(uint16_t)(f+step);
        *dst=(uint8_t)((*dst&0xf0u)|(r52map[b]&15u));
        dst+=152; count-=2;
    }
#endif
    if(count) {
        uint8_t ci=source[f>>9]; if(colormap)ci=colormap[ci];
        *dst=(uint8_t)((*dst&0x0fu)|((r52map[ci]&15u)<<4));
    }
#endif /* R49 V optimized path */
#else
    if(x&1){
        do {
            uint8_t ci=source[f>>9];
            if(colormap)ci=colormap[ci];
            uint8_t c=(uint8_t)(r52map[ci]&15);
#if defined(DOOM_R42_WALL_ASM)
            __asm__ volatile(
                "move.b (%[ptr]),%%d0\n\t"
                "andi.b #0xf0,%%d0\n\t"
                "or.b %[col],%%d0\n\t"
                "move.b %%d0,(%[ptr])"
                :: [ptr] "a" (dst), [col] "d" (c)
                : "d0","cc","memory");
#else
            *dst=(uint8_t)((*dst&0xf0u)|c);
#endif
            dst+=R22_PITCH; f=(uint16_t)(f+step);
        }while(--remaining);
    }else{
        do {
            uint8_t ci=source[f>>9];
            if(colormap)ci=colormap[ci];
            uint8_t c=(uint8_t)((r52map[ci]&15)<<4);
#if defined(DOOM_R42_WALL_ASM)
            __asm__ volatile(
                "move.b (%[ptr]),%%d0\n\t"
                "andi.b #0x0f,%%d0\n\t"
                "or.b %[col],%%d0\n\t"
                "move.b %%d0,(%[ptr])"
                :: [ptr] "a" (dst), [col] "d" (c)
                : "d0","cc","memory");
#else
            *dst=(uint8_t)((*dst&0x0fu)|c);
#endif
            dst+=R22_PITCH; f=(uint16_t)(f+step);
        }while(--remaining);
    }
#endif /* Pair-V column renderer */
}
void R_DrawColumnWall(const draw_column_vars_t *v){R42_DrawPackedWall(v);}
#else
void R_DrawColumnWall(const draw_column_vars_t *v){R_DrawColumnSprite(v);}
#endif
void R_DrawFuzzColumn(const draw_column_vars_t *v){R_DrawColumnSprite(v);}
void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){
    const uint8_t *r52map=r22_color;
#if defined(DOOM_R56_DUAL_COLOR)
    r52map=(v->x&1u)?r56_flat_odd:r56_flat_even;
#elif defined(DOOM_R55_FLAT_SAFE)
    r52map=(v->x&1u)?r55_flat_odd:r55_flat_even;
#elif defined(DOOM_R52_AB)
    r52map=(v->x&1u)?r52_odd:r52_even;
#endif
#if defined(DOOM_R47_FLAT_HOIST)
    /* R47A: eliminate per-pixel bounds/level checks and y*38 addressing.
     * Exactly one framebuffer byte is modified per visible sample;
     * the neighbouring nibble is preserved (required for 4x4 floors).
     * Does not alter R39f's independent 8x8 backend. */
    int16_t x=v->x, y0=v->yl, y1=v->yh;
    if(y1<y0 || (uint16_t)x>=R22_W) return;
#if defined(DOOM_R57_CROP16)
    int16_t border=(_g_gamestate==GS_LEVEL)?(R57_CROP_ACTIVE?R57_YMIN:2):0;
    if((_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE) && x>=R57_XEND)return;
    if((_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE) && y1>=R57_YEND)y1=R57_YEND-1;
#else
    int16_t border=(_g_gamestate==GS_LEVEL)?2:0;
#endif
    if(x<border) return;
    if(y0<border)y0=border;
    if(y0<0)y0=0;
    if(y1>=R22_H)y1=R22_H-1;
    if(y0>y1)return;
    R48_COUNT(R48_FLAT_CALLS,1);
    R48_COUNT(R48_FLAT_PIXELS,(uint16_t)(y1-y0+1));
    uint8_t sample=(uint8_t)(r52map[c]&15u);
    uint8_t keep=(x&1)?0xf0u:0x0fu;
    uint8_t put=(x&1)?sample:(uint8_t)(sample<<4);
    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)y0);
#if defined(DOOM_R48_PAIR_V)
    uint16_t count=(uint16_t)(y1-y0+1);
#if defined(DOOM_R49_COLORMIX)
    const uint8_t gate=r49_gate_current[c];
#endif
    if((y0&1) && count) {
        *dst=(uint8_t)((*dst&0xf0u)|sample);
#if defined(DOOM_R49_COLORMIX)
        R49_WriteMixFlag(dst,y0,gate);
#endif
        dst+=152; --count;
    }
#if defined(DOOM_R48_V_FAST)
    const uint8_t pair=(uint8_t)(sample*0x11u);
    while(count>=2) {
        *dst=pair;
#if defined(DOOM_R49_COLORMIX)
        dst[-1]=R49_TileAttr(gate?3u:0u);
#endif
        dst+=152; count-=2;
    }
#else
    while(count>=2) {
        *dst=(uint8_t)((*dst&0x0fu)|(sample<<4));
        *dst=(uint8_t)((*dst&0xf0u)|sample);
        dst+=152; count-=2;
    }
#endif
    if(count) {
        *dst=(uint8_t)((*dst&0x0fu)|(sample<<4));
#if defined(DOOM_R49_COLORMIX)
        R49_WriteMixFlag(dst,0,gate);
#endif
    }
#else
    uint16_t n=(uint16_t)(y1-y0);
    do {
        *dst=(uint8_t)((*dst&keep)|put);
        dst+=R22_PITCH;
    } while(n--);
#endif
#else
    c=r52map[c];for(int16_t y=v->yl;y<=v->yh;y++)R22_Plot(v->x,y,c);
#endif
}
void I_ReloadPalette(void) { /* Palette tables generated from the embeddedPLAYPAL. */ }
void I_SetPalette(int8_t p){r22_newpal=p;}
void V_SetSTPalette(void){}
static void R22_Palette(int8_t p){
    if(p<0)p=0;if(p>13)p=13;
#if defined(DOOM_R56_DUAL_COLOR)
    PAL_setColors(0,r56_pal0[(uint8_t)p],16,DMA);
    PAL_setColors(16,r56_pal1[(uint8_t)p],16,DMA);
#elif defined(DOOM_R52_AB)
    PAL_setColors(0,r52_pal0+(uint16_t)(uint8_t)p*16u,16,DMA);
    PAL_setColors(16,r52_pal1+(uint16_t)(uint8_t)p*16u,16,DMA);
#else
    PAL_setColors(0,r22_cram[(uint8_t)p],16,DMA);
#endif
#if defined(DOOM_R51_HW_WEAPON)
    /* Palette2: weapon colors remapped to each PLAYPAL tint.
     * World PAL0 and ColorMix PAL1 remain unchanged. */
    PAL_setColors(32,r51_weapon_pal2[(uint8_t)p],16,DMA);
#endif
#if defined(DOOM_R49_COLORMIX)
    PAL_setColors(16,r49_palette1+(uint16_t)p*16u,16,DMA);
    r49_gate_current=r49_mix_ok+(uint16_t)p*256u;
#if defined(DOOM_R49_COMPLUT)
    r49_compgate_current=r49_compgate+(uint32_t)(uint16_t)p*R49_COLORMAP_BYTES;
#endif
#endif
}

#if defined(DOOM_R47_PLANE_PAIR)
#if defined(DOOM_R53_MICRO)
/* 4x4 scene samples retain their geometry. Inside each immutable 8x8 tile,
 * four opaque physical pixels alternate between two colors from the SAME
 * VDP palette. Each attribute word selects one 16-entry palette, so this
 * is a PAL-local optical mix, not 1px PAL0/PAL1 cross-blending.
 * Rows y mod4 disperse the pattern; index zero stays transparent. */
static inline uint32_t R53_MicroRow(uint8_t base,uint8_t partner,uint16_t row)
{
    if(base==0)return 0; /* never turn transparent source pixels opaque */
    uint32_t word=0;
    for(uint16_t x=0;x<4;x++){
#if DOOM_R53_MICRO == 25
        uint16_t select=((x+row)&3u)==0u;
#else
        uint16_t select=((x+row)&1u)==0u;
#endif
        uint8_t nib=(uint8_t)(select?partner:base);
        word|=(uint32_t)nib<<(28u-x*4u);
    }
    return word;
}
#endif
#if defined(DOOM_R56_DUAL_COLOR)
/* Each pair CODE owns two CRAM slots; each opaque 4px half is ABAB.
 * Plane B is the same left-opaque tile shifted right by 4px (Pair-V). */
static inline uint32_t R56_PairRow(uint8_t code,const uint8_t pairs[16][2])
{
    if(code==0u)return 0u;
    uint32_t a=pairs[code][0],b=pairs[code][1];
    return (a<<28)|(b<<24)|(a<<20)|(b<<16);
}
#endif
static void R47_LoadPairTiles(void)
{
    uint32_t tile[8];
    for(uint16_t p=0;p<256;p++){
#if defined(DOOM_R48_PAIR_V)
        /* Pair-V: upper/lower logical samples share an 8px-high tile.
         * Only left four physical pixels are opaque; Plane B is shifted +4. */
        uint8_t hi=(uint8_t)(p>>4),lo=(uint8_t)(p&15);
#if defined(DOOM_R56_DUAL_COLOR)
        for(uint16_t y=0;y<8;y++)
            tile[y]=R56_PairRow((y<4u)?hi:lo,r56_pairs_even);
#elif defined(DOOM_R53_MICRO)
        for(uint16_t y=0;y<8;y++){
            uint8_t base=(y<4u)?hi:lo;
            tile[y]=R53_MicroRow(base,r53_partner_even[base],y&3u);
        }
#else
#if defined(DOOM_R48_V_DITHER50) || defined(DOOM_R48_V_DITHER75A) || defined(DOOM_R48_V_DITHER75B)
        /* Tonal experiments with fixed partner table: NOT a measured
         * perceptually optimal mapper. No RGB search at runtime. */
        static const uint8_t partner[16]={0,1,3,2,6,2,4,10,11,9,12,14,10,12,15,14};
#if defined(DOOM_R48_V_DITHER75A)
        uint32_t upper=((uint32_t)hi*0x11100000u)|((uint32_t)partner[hi]*0x00010000u);
        uint32_t lower=((uint32_t)lo*0x11100000u)|((uint32_t)partner[lo]*0x00010000u);
#elif defined(DOOM_R48_V_DITHER75B)
        uint32_t upper=((uint32_t)hi*0x10000000u)|((uint32_t)partner[hi]*0x01110000u);
        uint32_t lower=((uint32_t)lo*0x10000000u)|((uint32_t)partner[lo]*0x01110000u);
#else
        uint32_t upper=((uint32_t)hi*0x11000000u)|((uint32_t)partner[hi]*0x00110000u);
        uint32_t lower=((uint32_t)lo*0x11000000u)|((uint32_t)partner[lo]*0x00110000u);
#endif
#else
        uint32_t upper=(uint32_t)hi*0x11110000u;
        uint32_t lower=(uint32_t)lo*0x11110000u;
#endif
        tile[0]=tile[1]=tile[2]=tile[3]=upper;
        tile[4]=tile[5]=tile[6]=tile[7]=lower;
#endif /* R53_MICRO */
#else
        const uint32_t top=R22_ExpandPair((uint8_t)p);
        tile[0]=tile[1]=tile[2]=tile[3]=top;
        tile[4]=tile[5]=tile[6]=tile[7]=0;
#endif
        VDP_loadTileData(tile,R22_PAIR_TILE_BASE+p,1,CPU);
#if defined(DOOM_R56_DUAL_COLOR)
        for(uint16_t y=0;y<8;y++)
            tile[y]=R56_PairRow((y<4u)?hi:lo,r56_pairs_odd);
        VDP_loadTileData(tile,(uint16_t)(R22_PAIR_TILE_BASE+256u+p),1,CPU);
#elif defined(DOOM_R53_MICRO)
        for(uint16_t y=0;y<8;y++){
            uint8_t base=(y<4u)?hi:lo;
            tile[y]=R53_MicroRow(base,r53_partner_odd[base],y&3u);
        }
        VDP_loadTileData(tile,(uint16_t)(R22_PAIR_TILE_BASE+256u+p),1,CPU);
#endif
#if defined(DOOM_R49_COLORMIX)
        /* Four pattern banks encode the independent "eligible" bits from
         * top/bottom nibble writes. Banks 1/2 intentionally reproduce PAL0
         * exactly; only both flags true (bank3) changes palette and pixels.
         * All banks fit under the font tile at 1440, no added WRAM. */
        for(uint16_t bank=1;bank<4;bank++){
            if(bank==3){
                uint8_t au=r49_mix_a[hi],bu=r49_mix_b[hi];
                uint8_t al=r49_mix_a[lo],bl=r49_mix_b[lo];
#if defined(DOOM_R49_MIX_75A)
                uint32_t u=(uint32_t)au*0x11100000u+(uint32_t)bu*0x00010000u;
                uint32_t l=(uint32_t)al*0x11100000u+(uint32_t)bl*0x00010000u;
#elif defined(DOOM_R49_MIX_75B)
                uint32_t u=(uint32_t)au*0x10000000u+(uint32_t)bu*0x01110000u;
                uint32_t l=(uint32_t)al*0x10000000u+(uint32_t)bl*0x01110000u;
#else
                uint32_t u=(uint32_t)au*0x11000000u+(uint32_t)bu*0x00110000u;
                uint32_t l=(uint32_t)al*0x11000000u+(uint32_t)bl*0x00110000u;
#endif
                tile[0]=tile[1]=tile[2]=tile[3]=u;
                tile[4]=tile[5]=tile[6]=tile[7]=l;
            }
            VDP_loadTileData(tile,(uint16_t)(R22_PAIR_TILE_BASE+bank*256u+p),1,CPU);
        }
#endif
    }
}
static void R47_ClearPairBuffer(void)
{
    uint16_t *w=(uint16_t *)(void *)r22_fb.pixels;
#if defined(DOOM_R52_AB)
    /* Pair-V y blocks: A (even x) uses PAL0, B (odd x) PAL1.
     * Attribute high bytes survive 38-word VBlank DMA intact. */
    for(uint16_t y=0;y<R22_H/2u;y++){
        for(uint16_t x=0;x<38u;x++)w[y*76u+x]=(uint16_t)R22_PAIR_TILE_BASE;
#if defined(DOOM_R53_MICRO) || defined(DOOM_R56_DUAL_COLOR)
        for(uint16_t x=38u;x<76u;x++)w[y*76u+x]=(uint16_t)(0x2000u|R22_PAIR_TILE_BASE+256u);
#else
        for(uint16_t x=38u;x<76u;x++)w[y*76u+x]=(uint16_t)(0x2000u|R22_PAIR_TILE_BASE);
#endif
    }
#else
    for(uint16_t i=0;i<38*R22_H;i++)w[i]=(uint16_t)R22_PAIR_TILE_BASE;
#endif
}
#endif

#if defined(DOOM_R35_ART_RAW)
#include "r35_native4.inc"
#endif

/* Main and ISR share ownership of the back bank only at this publication. */
void R20_VBlankVideo(void){
    if(!r22_ready)return;
    uint16_t line=(*(volatile uint16_t*)0xC00008)>>8;
    if(line<224||line>232)return;
    R20_PROBE();
    if(r22_queued_pal!=100)R22_Palette(r22_queued_pal);
    uint16_t sr;__asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr":"=d"(sr)::"cc","memory");
    bool bus=Z80_getAndRequestBus(TRUE);VDP_setAutoInc(2);
    volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;
#if defined(DOOM_R47_PLANE_PAIR)
    /* Each sample row already is 38 VDP tile words (0x0100 | color-pair).
     * A receives even rows; B receives odd rows and is vertically shifted
     * by -4 pixels. No dynamic pattern upload is required. */
#if defined(DOOM_R48_PAIR_V)
    const uint16_t *srca=(const uint16_t *)(const void *)(r22_fb.pixels+152);
    const uint16_t *srcb=(const uint16_t *)(const void *)(r22_fb.pixels+152+76);
#else
    const uint16_t *srca=R22_PairRow(r22_fb.pixels,2);
    const uint16_t *srcb=R22_PairRow(r22_fb.pixels,3);
#endif
    uint16_t dsta=VDP_BG_A+128,dstb=VDP_BG_B+128;
    uint16_t first_row=1,end_row=22,words_per_row=38;
#if defined(DOOM_R57_CROP16)
    if(r57_queued_crop){
        first_row=R57_TILE_YMIN;end_row=R57_TILE_YEND;
        words_per_row=R57_DMA_WORDS;
        srca+=(first_row-1)*76+R57_TILE_XMIN;
        srcb+=(first_row-1)*76+R57_TILE_XMIN;
        dsta+=(first_row-1)*128+R57_TILE_XMIN*2;
        dstb+=(first_row-1)*128+R57_TILE_XMIN*2;
    }
#endif
    for(uint16_t y=first_row;y<end_row;y++,srca+=76,srcb+=76,dsta+=128,dstb+=128){
        uint32_t a=((uint32_t)(uintptr_t)srca)>>1;
        *ctrl=0x9300|words_per_row;*ctrl=0x9400;
        *ctrl=0x9500|(a&255);*ctrl=0x9600|((a>>8)&255);*ctrl=0x9700|((a>>16)&127);
        volatile uint32_t command=VDP_DMA_VRAM_ADDR(dsta);
        volatile uint16_t *words=(volatile uint16_t*)&command;
        *ctrl=words[0];
        __asm__ volatile("move.w %0,(%1)"::"m"(words[1]),"a"(ctrl):"cc","memory");
        if(!r22_overlay_dirty){
            a=((uint32_t)(uintptr_t)srcb)>>1;
            *ctrl=0x9300|words_per_row;*ctrl=0x9400;
            *ctrl=0x9500|(a&255);*ctrl=0x9600|((a>>8)&255);*ctrl=0x9700|((a>>16)&127);
            command=VDP_DMA_VRAM_ADDR(dstb);
            words=(volatile uint16_t*)&command;
            *ctrl=words[0];
            __asm__ volatile("move.w %0,(%1)"::"m"(words[1]),"a"(ctrl):"cc","memory");
        }
    }
#else
    #if defined(DOOM_R22_SOLID_TILES)
    const uint16_t *src=r22_map;
    #else
    const uint16_t *src=&r22_maps[r22_next_bank][38];
    #endif
    /* Row0 is persistent text/FPS. Flip the21 graphics rows below it. */
    uint16_t dst=VDP_BG_A+128;
    for(uint16_t y=1;y<22;y++,src+=38,dst+=128){
        uint32_t a=((uint32_t)(uintptr_t)src)>>1;
        *ctrl=0x9300|38;*ctrl=0x9400;
        *ctrl=0x9500|(a&255);*ctrl=0x9600|((a>>8)&255);*ctrl=0x9700|((a>>16)&127);
        volatile uint32_t command=VDP_DMA_VRAM_ADDR(dst);
        volatile uint16_t *words=(volatile uint16_t*)&command;
        *ctrl=words[0];
        __asm__ volatile("move.w %0,(%1)"::"m"(words[1]),"a"(ctrl):"cc","memory");
    }
#endif
    if(!bus)Z80_releaseBus();
    __asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");
#if !defined(DOOM_R47_PLANE_PAIR)
    r22_front=r22_next_bank;
#endif
    __asm__ volatile("":::"memory");r22_ready=0;
}
void R20_AbortVideo(void){uint16_t sr;__asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr":"=d"(sr)::"cc","memory");r22_ready=0;r22_newpal=100;__asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");}
void R20_StopVideo(void){
    R48_COUNT(R48_WAIT_CALLS,1);
    while(r22_ready){
        R48_COUNT(R48_WAIT_SPINS,1);
        if(_g_vblankCount-r22_queued>180)I_Error("PX4 VBlank timeout");
    }
}

#if !defined(DOOM_R47_PLANE_PAIR)
static inline uint32_t R22_Expand(uint8_t p){
#if defined(DOOM_R22_PAIR_LUT)
    return r22_pair_lut[p];
#else
    return R22_ExpandPair(p);
#endif
}
static void R22_UploadBack(uint16_t bank){
    volatile uint32_t *data=(volatile uint32_t*)0xC00000,*ctrl=(volatile uint32_t*)0xC00004;
    uint16_t tile=(uint16_t)(16+bank*R22_TILES+38);
#if defined(DOOM_R22_SOLID_TILES)
    uint16_t *map=r22_map;
#endif
    for(uint16_t y=1;y<22;y++)for(uint16_t x=0;x<38;x++,tile++){
        uint8_t a=r22_fb.pixels[(2*y)*38+x],b=r22_fb.pixels[(2*y+1)*38+x];
#if defined(DOOM_R22_SOLID_TILES)
        uint16_t index=R22_TileIndex(a,b,tile);*map++=index;
        if(index<16)continue;
#endif
        uint32_t top=R22_Expand(a),bottom=R22_Expand(b);
        uint16_t sr=R22_Lock();
        VDP_setAutoInc(2);*ctrl=VDP_WRITE_VRAM_ADDR(tile*32u);
        *data=top;*data=top;*data=top;*data=top;
        *data=bottom;*data=bottom;*data=bottom;*data=bottom;
        R22_Unlock(sr);
    }
}
#endif

static void R22_Text(int16_t x,int16_t y,const char *s){
#if defined(DOOM_R35_ART_RAW)
    if(r35_native_active>=0){
        R40B_DrawNativeText(x,y,s);
        return;
    }
#endif
    if(x<0||x>=38||y<0||y>=22)return;
    /* Window is independently addressable at F000. Plane B intentionally
       mirrors A at E000: transparent Window pixels reveal the same raster.
       Window rows24..31 contain SAT/HScroll at FC00, never text. */
    if(y>0){
        /* Preserve the old menu throughout slow raster rendering. Clear it
           only when the replacement text is actually ready to be drawn. */
        if(!r22_text_this_frame){R22_ClearOverlay();r22_text_this_frame=1;}
        R20_StopVideo();uint16_t sr=R22_Lock();
        VDP_setWindowHPos(TRUE,0);VDP_setWindowVPos(FALSE,0);
        R22_Unlock(sr);r22_overlay_dirty=1;
    }
    R22_DrawText(y==0?VDP_BG_A:VDP_WINDOW,s,(uint16_t)x,(uint16_t)y);
}
void V_DrawCharacter(int16_t x,int16_t y,uint8_t c,char ch){(void)c;char b[2]={ch,0};if(ch==1||ch==2)b[0]='>';if((uint8_t)b[0]<32||(uint8_t)b[0]>127)b[0]=' ';R22_Text(x,y,b);}
void V_DrawCharacterForeground(int16_t x,int16_t y,uint8_t c,char ch){V_DrawCharacter(x,y,c,ch);}
void V_DrawSTCharacter(int16_t x,int16_t y,uint8_t c,char ch){V_DrawCharacter(x,y,c,ch);}
void V_DrawString(int16_t x,int16_t y,uint8_t c,const char *s){(void)c;R22_Text(x,y,s);}
void V_DrawSTString(int16_t x,int16_t y,uint8_t c,const char *s){V_DrawString(x,y,c,s);}
void V_ClearString(int16_t y,size_t n){for(uint16_t x=0;x<n&&x<38;x++)V_DrawCharacter(x,y,0,' ');}
void R22_BeginFrame(void){
    /* Complete the old flip before VDP use, retaining the displayed menu
       throughout title/raster work. Text replacement happens just-in-time. */
    R20_StopVideo();r22_text_this_frame=0;
#if defined(DOOM_R57_H32)
    R57_VideoMode();
#endif
#if defined(DOOM_R51_HW_WEAPON)
    R51_WeaponBeginFrame();
#endif
#if defined(DOOM_R35_ART_RAW)
    if(r35_native_active>=0)
        memset(r40b_native_seen,0,R40B_OCC_BYTES);
#endif
}
static void R22_EndOverlay(void){
#if defined(DOOM_R35_ART_RAW)
    if(r35_native_active>=0){
#if defined(DOOM_R50_STATIC_MENU)
        /* The native picture remains visible on both background planes.
         * Remove glyphs that are no longer requested, including the case
         * where the menu was closed on this frame. */
        if(r22_overlay_dirty || r22_text_this_frame)
            R40B_PruneNativeText();
        r22_overlay_dirty=(r22_text_this_frame!=0);
#else
        if(r22_overlay_dirty && !r22_text_this_frame){
            R22_ClearOverlay();
            R40B_ResetNativeText();
        } else if(r22_text_this_frame){
            R40B_PruneNativeText();
        }
#endif
        return;
    }
#endif
    if(r22_overlay_dirty && !r22_text_this_frame)R22_ClearOverlay();
}
void V_ClearViewWindow(void){
#if defined(DOOM_R50_STATIC_MENU) && defined(DOOM_R35_ART_RAW)
    /* R40b reuses the otherwise idle Pair-V framebuffer as the two glyph
     * occupancy bitsets (prev + seen). M_Drawer calls I_InitScreenPage()
     * every frame, and wipe_StartScreen() may do so too. Resetting the
     * framebuffer here destroys the records needed to retire old glyphs,
     * leaving superseded menu text burned into the native art.
     * Native 320x224 art already resides entirely in VDP VRAM; it has NO
     * software framebuffer to clear. Guard every aliasing clear path. */
    if(r35_native_active>=0)return;
#endif
#if defined(DOOM_R47_PLANE_PAIR)
    R47_ClearPairBuffer();
#else
    memset(r22_fb.pixels,0,R22_FB_BYTES);
#endif
}

void V_DrawBackground(int16_t n){(void)n;V_ClearViewWindow();}
void V_DrawRawFullScreen(int16_t n){
#if defined(DOOM_R35_ART_RAW)
    if(R35_DrawNative4(n))return;
    if(r35_native_active>=0)R35_LeaveNative4();
#endif
    const uint8_t *p=W_GetLumpByNum(n);V_ClearViewWindow();
    for(uint16_t y=0;y<44;y++)for(uint16_t x=0;x<76;x++)R22_Put(r22_fb.pixels,x,y,r22_color[p[(y*SCREENHEIGHT/44)*SCREENWIDTH+x*SCREENWIDTH/76]]);
}
void V_InitDrawLine(void){}void V_ShutdownDrawLine(void){}
void V_DrawLine(int16_t x,int16_t y,int16_t xx,int16_t yy,uint8_t c){
    int16_t dx=abs(xx-x),sx=x<xx?1:-1,dy=-abs(yy-y),sy=y<yy?1:-1,e=dx+dy;c=r22_color[c];
    for(;;){R22_Plot(x,y,c);if(x==xx&&y==yy)break;int16_t e2=2*e;if(e2>=dy){e+=dy;x+=sx;}if(e2<=dx){e+=dx;y+=sy;}}
}
void I_InitScreenPage(void){V_ClearViewWindow();}void I_InitScreenPages(void){V_ClearViewWindow();}
void wipe_StartScreen(void){V_ClearViewWindow();}void D_Wipe(void){I_FinishUpdate();}
#if defined(DOOM_R51_HW_HUD)
/* Window replaces Plane A, rather than transparently compositing with it.
 * Bottom HUD text therefore MUST be written to Window at high priority;
 * the black Window fill itself uses low priority so it masks low-priority
 * gun sprites, with no horizontal interrupt. */
#define R51_HUD_TEXT_PLANE VDP_WINDOW
#else
#define R51_HUD_TEXT_PLANE VDP_BG_A
#endif
static void R22_Num3(uint16_t x,uint16_t y,int32_t v){if(v<0)v=0;if(v>999)v=999;char s[4]={(char)('0'+v/100),(char)('0'+v/10%10),(char)('0'+v%10),0};R22_DrawText(R51_HUD_TEXT_PLANE,s,x,y);}
static void R22_HUD(void){
#if defined(DOOM_R51_HW_HUD)
    if(!_g_menuactive)R51_HudMaskPrepare();
#endif
    static uint16_t health=65535,armor=65535,ammo=65535;
    uint16_t h=_g_player.mo?_g_player.mo->health:_g_player.health,a=_g_player.armorpoints,b=_g_player.ammo[am_clip];
    VDP_setTextPlane(BG_A);VDP_setTextPalette(PAL0);VDP_setTextPriority(TRUE);
    if(h!=health||a!=armor||b!=ammo
#if defined(DOOM_R57_NARROW256)
       ||r57_hud_dirty
#endif
#if defined(DOOM_R51_HW_HUD)
       ||r51_hud_text_dirty
#endif
    ){
#if defined(DOOM_R57_NARROW256)
        {
            R22_DrawText(R51_HUD_TEXT_PLANE,"H",1,23);R22_Num3(3,23,h);
            R22_DrawText(R51_HUD_TEXT_PLANE,"A",10,23);R22_Num3(12,23,a);
            R22_DrawText(R51_HUD_TEXT_PLANE,"AMMO",20,23);R22_Num3(25,23,b);
            R22_DrawText(R51_HUD_TEXT_PLANE,"DOOM PX4 - 256",1,25);
        }
#else
        R22_DrawText(R51_HUD_TEXT_PLANE,"HEALTH",1,23);R22_Num3(8,23,h);R22_DrawText(R51_HUD_TEXT_PLANE,"ARMOR",13,23);R22_Num3(19,23,a);
        R22_DrawText(R51_HUD_TEXT_PLANE,"BULLETS",24,23);R22_Num3(32,23,b);health=h;armor=a;ammo=b;
        R22_DrawText(R51_HUD_TEXT_PLANE,"DOOM PX4 - 76x44",1,25);
#endif
#if defined(DOOM_R57_NARROW256)
        health=h;armor=a;ammo=b;r57_hud_dirty=0;
#endif
#if defined(DOOM_R51_HW_HUD)
        r51_hud_text_dirty=0;
#endif
    }
    static uint32_t vb;static uint16_t frames;frames++;
    uint32_t dt=_g_vblankCount-vb;if(dt>=60){uint16_t f=(uint32_t)frames*600/dt;if(f>999)f=999;char s[8]={(char)('0'+f/100),(char)('0'+f/10%10),'.',(char)('0'+f%10),'f','p','s',0};R22_DrawText(VDP_BG_A,s,
#if defined(DOOM_R57_NARROW256)
        24,
#else
        31,
#endif
        0);frames=0;vb=_g_vblankCount;}
}
void I_FinishUpdate(void){
#if defined(DOOM_R35_ART_RAW)
    if(r35_native_active>=0){
        if(_g_gamestate!=GS_LEVEL){
#if defined(DOOM_R51_HW_WEAPON)
            R51_WeaponInvalidate();
#endif
            /* R40a: This branch skips regular pixel4 presentation, but
             * must still retire the previous WINDOW overlay on frames
             * without a menu (for example, after Start closes it). */
            R22_EndOverlay();
            return; /* Native picture remains in VRAM. */
        }
        R35_LeaveNative4(); /* Gameplay uses the original p4 pipeline. */
#if defined(DOOM_R57_H32)
        if(r57_h32_active){VDP_setHorizontalScroll(BG_A,-24);VDP_setHorizontalScroll(BG_B,-20);}
#endif
    }
#endif
    if(r22_fb.before!=R22_GUARD||r22_fb.after!=R22_GUARD)I_Error("PX4 framebuffer guard");
    R20_StopVideo();R22_EndOverlay();
#if defined(DOOM_R57_CROP16)
    r57_queued_crop=(_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE);
    if(r57_queued_crop && !r57_was_level)R57_ClearBorder();
    r57_was_level=r57_queued_crop;
#endif
#if defined(DOOM_R20_STACKGUARD)
    static uint8_t sample;R20_PROBE();if((sample++&15u)==0)R20_DiagSample();
#endif
#if defined(DOOM_R47_PLANE_PAIR)
    if(_g_gamestate==GS_LEVEL)R22_HUD();
    r22_next_bank=0;r22_queued_pal=r22_newpal;r22_newpal=100;r22_queued=_g_vblankCount;
#else
    uint16_t back=r22_front^1;R22_UploadBack(back);
    if(_g_gamestate==GS_LEVEL)R22_HUD();
    r22_next_bank=back;r22_queued_pal=r22_newpal;r22_newpal=100;r22_queued=_g_vblankCount;
#endif
#if defined(DOOM_R51_HW_WEAPON)
    R51_WeaponPresent();
#endif
    __asm__ volatile("":::"memory");r22_ready=1;
#if defined(TIMEDEMO) || defined(DOOM_R50_PLAY_BENCH)
    I_BenchmarkFrame();
#endif
}
void I_InitGraphicsHardwareSpecificCode(void){
    R20_StopVideo();VDP_setScreenWidth320();VDP_setPlaneSize(64,32,FALSE);
#if defined(DOOM_R47_PLANE_PAIR)
    /* Fixed non-moving R47 layout: pair patterns 256..511; font B400..BFFF. */
    VDP_setBGBAddress(0xC000);VDP_setWindowAddress(0xD000);
    VDP_setSpriteListAddress(0xF400);VDP_setHScrollTableAddress(0xF000);
    VDP_setBGAAddress(0xE000);
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,0);
    if(TILE_FONT_INDEX!=1440 || VDP_BG_A!=0xE000 || VDP_BG_B!=0xC000 || VDP_WINDOW!=0xD000)
        I_Error("R47 pair VDP/font layout");
    VDP_clearPlane(BG_A,TRUE);VDP_clearPlane(BG_B,TRUE);VDP_clearPlane(WINDOW,TRUE);
    VDP_setHorizontalScroll(BG_A,0);VDP_setHorizontalScroll(BG_B,0);
    VDP_setVerticalScroll(BG_A,0);
#if defined(DOOM_R48_PAIR_V)
    VDP_setVerticalScroll(BG_B,0);
    VDP_setHorizontalScroll(BG_B,4);
#else
    VDP_setVerticalScroll(BG_B,-4);
#endif
#else
    /* All map/table addresses>=E000, soSGDK relocates its96font tiles to
       D400..DFFF, above both graphics banks (endingD2FF). */
    VDP_setBGBAddress(0xE000);VDP_setWindowAddress(0xF000);VDP_setSpriteListAddress(0xFC00);VDP_setHScrollTableAddress(0xFC00);VDP_setBGAAddress(0xE000);
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,0);
    if(TILE_FONT_INDEX!=1696 || VDP_BG_A!=0xE000 || VDP_BG_B!=0xE000 || VDP_WINDOW!=0xF000)
        I_Error("PX4 VDP/font layout");
    VDP_clearPlane(BG_A,TRUE);VDP_clearPlane(WINDOW,TRUE);
    VDP_setHorizontalScroll(BG_A,0);VDP_setHorizontalScroll(BG_B,0);VDP_setVerticalScroll(BG_A,0);VDP_setVerticalScroll(BG_B,0);
#endif
    /* Explicit solid tiles also guarantee transparent tile0 for Window.
       Do not rely on the SDK's initial contents surviving font relocation. */
    uint16_t sr=R22_Lock();
    volatile uint32_t *data=(volatile uint32_t*)0xC00000,*ctrl=(volatile uint32_t*)0xC00004;
    VDP_setAutoInc(2);*ctrl=VDP_WRITE_VRAM_ADDR(0);
    for(uint16_t c=0;c<16;c++){uint32_t row=(uint32_t)c*0x11111111u;for(uint16_t y=0;y<8;y++)*data=row;}
    R22_Unlock(sr);
#if defined(DOOM_R47_PLANE_PAIR)
    R47_LoadPairTiles();
#endif
    R22_InitOpenings();R22_Palette(0);r22_newpal=100;
#if defined(DOOM_R51_HW_WEAPON)
    R51_WeaponInvalidate();
#endif
    r22_fb.before=r22_fb.after=R22_GUARD;
#if defined(DOOM_R47_PLANE_PAIR)
    R47_ClearPairBuffer();
#else
    memset(r22_fb.pixels,0,R22_FB_BYTES);
#endif
    r22_front=0;r22_ready=0;
#if defined(DOOM_R50_RESET_SRAM)
    /* Some soft-reset paths preserve VDP display-enable state. Make the
     * normal 3D/title pipeline explicitly visible after SRAM/ROM recovery. */
    VDP_waitDMACompletion();
    VDP_setEnable(TRUE);
#endif
#if defined(DOOM_R22_PATTERN)
    for(uint16_t y=0;y<44;y++)for(uint16_t x=0;x<76;x++)R22_Put(r22_fb.pixels,x,y,(uint8_t)((x+y)&15));
    I_FinishUpdate();R20_StopVideo();VDP_setTextPlane(BG_A);R22_DrawText(VDP_BG_A,"PX4: EACH SQUARE IS 4x4",1,0);
    for(;;)SYS_doVBlankProcess();
#endif
}
void I_ShutdownGraphics(void){R20_StopVideo();}
