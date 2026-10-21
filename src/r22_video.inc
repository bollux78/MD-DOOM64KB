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
#if defined(DOOM_R43_GRAY_CRT)
#include "r43_gray_palette.h" /* 4x4 CRAM/LUT only; Bayer8 still unchanged. */
#else
#include "r22_palette.h"
#endif
#include "r22_maps.h"
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
/* SDK text helpers use a 256-byte stack array. Write bounded glyphs directly,
   with exclusive ownership of the VDP address/data ports for the whole string. */
static void R22_DrawText(uint16_t plane,const char *s,uint16_t x,uint16_t y){
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
static void R40B_DrawNativeText(int16_t x,int16_t y,const char *s)
{
    if(x<0||x>=R40B_TEXT_W||y<0||y>=R40B_TEXT_H)return;
    if(!r22_text_this_frame){
        R20_StopVideo();
        uint16_t sr=R22_Lock();
        VDP_setWindowHPos(TRUE,0);
        VDP_setWindowVPos(FALSE,0);
        R22_Unlock(sr);
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
    R22_DrawText(VDP_WINDOW,s,(uint16_t)x,(uint16_t)y);
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
                    if(!run)*ctrl=VDP_WRITE_VRAM_ADDR(VDP_WINDOW+y*128u+x*2u);
                    *data=0; /* Transparent WINDOW cell shows native art. */
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
    VDP_clearPlane(WINDOW, TRUE);
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,0);
    VDP_setTextPlane(BG_A);
    VDP_setTextPriority(TRUE);
}
#endif


#include "r22_benchmark.inc"

static inline void R22_Plot(int16_t x,int16_t y,uint8_t c) {
    if((uint16_t)x>=R22_W || (uint16_t)y>=R22_H)return;
    /* Same8px top/left safety border as the38x22 reference. */
    if(_g_gamestate==GS_LEVEL && (x<2 || y<2))return;
    R22_Put(r22_fb.pixels,(uint16_t)x,(uint16_t)y,c);
}
void R_DrawColumnSprite(const draw_column_vars_t *v) {
#if defined(DOOM_R47_SPRITE_HOIST)
    /* R47: same exact clipping/stride hoist as flats, while retaining the
     * sprite read-modify-write required to preserve the neighbouring nibble. */
    int16_t x=v->x, y0=v->yl, y1=v->yh;
    if(y1<y0 || (uint16_t)x>=R22_W)return;
    int16_t border=(_g_gamestate==GS_LEVEL)?2:0;
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
    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)first);
    uint16_t n=(uint16_t)(y1-first);
    if(x&1){
        do{
            uint8_t ci=source[frac>>9];if(colormap)ci=colormap[ci];
            *dst=(uint8_t)((*dst&0xf0u)|(r22_color[ci]&15u));
            dst+=R22_PITCH;frac=(uint16_t)(frac+step);
        }while(n--);
    }else{
        do{
            uint8_t ci=source[frac>>9];if(colormap)ci=colormap[ci];
            *dst=(uint8_t)((*dst&0x0fu)|((r22_color[ci]&15u)<<4));
            dst+=R22_PITCH;frac=(uint16_t)(frac+step);
        }while(n--);
    }
#else
    int16_t n=v->yh-v->yl+1;if(n<=0)return;
    uint16_t frac=(uint16_t)((v->texturemid>>7)+(v->yl-CENTERY)*v->fracstep);
    for(int16_t y=v->yl;y<=v->yh;y++) {
        uint8_t c=v->source[frac>>9];
        if(v->colormap)c=v->colormap[c];
        R22_Plot(v->x,y,r22_color[c]);frac+=v->fracstep;
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
    int16_t x=v->x, y0=v->yl, y1=v->yh;
    if(y1<y0 || (uint16_t)x>=R22_W) return;
    int16_t border=(_g_gamestate==GS_LEVEL)?2:0;
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
    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)first);
    int16_t remaining=(int16_t)(y1-first+1);
    if(x&1){
        do {
            uint8_t ci=source[f>>9];
            if(colormap)ci=colormap[ci];
            uint8_t c=(uint8_t)(r22_color[ci]&15);
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
            uint8_t c=(uint8_t)((r22_color[ci]&15)<<4);
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
}
void R_DrawColumnWall(const draw_column_vars_t *v){R42_DrawPackedWall(v);}
#else
void R_DrawColumnWall(const draw_column_vars_t *v){R_DrawColumnSprite(v);}
#endif
void R_DrawFuzzColumn(const draw_column_vars_t *v){R_DrawColumnSprite(v);}
void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){
#if defined(DOOM_R47_FLAT_HOIST)
    /* R47A: eliminate per-pixel bounds/level checks and y*38 addressing.
     * Exactly one framebuffer byte is modified per visible sample;
     * the neighbouring nibble is preserved (required for 4x4 floors).
     * Does not alter R39f's independent 8x8 backend. */
    int16_t x=v->x, y0=v->yl, y1=v->yh;
    if(y1<y0 || (uint16_t)x>=R22_W) return;
    int16_t border=(_g_gamestate==GS_LEVEL)?2:0;
    if(x<border) return;
    if(y0<border)y0=border;
    if(y0<0)y0=0;
    if(y1>=R22_H)y1=R22_H-1;
    if(y0>y1)return;
    R48_COUNT(R48_FLAT_CALLS,1);
    R48_COUNT(R48_FLAT_PIXELS,(uint16_t)(y1-y0+1));
    uint8_t sample=(uint8_t)(r22_color[c]&15u);
    uint8_t keep=(x&1)?0xf0u:0x0fu;
    uint8_t put=(x&1)?sample:(uint8_t)(sample<<4);
    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)y0);
    uint16_t n=(uint16_t)(y1-y0);
    do {
        *dst=(uint8_t)((*dst&keep)|put);
        dst+=R22_PITCH;
    } while(n--);
#else
    c=r22_color[c];for(int16_t y=v->yl;y<=v->yh;y++)R22_Plot(v->x,y,c);
#endif
}
void I_ReloadPalette(void) { /* Palette tables generated from the embeddedPLAYPAL. */ }
void I_SetPalette(int8_t p){r22_newpal=p;}
void V_SetSTPalette(void){}
static void R22_Palette(int8_t p){if(p<0)p=0;if(p>13)p=13;PAL_setColors(0,r22_cram[(uint8_t)p],16,DMA);}

#if defined(DOOM_R47_PLANE_PAIR)
static void R47_LoadPairTiles(void)
{
    uint32_t tile[8];
    for(uint16_t p=0;p<256;p++){
        const uint32_t top=R22_ExpandPair((uint8_t)p);
        tile[0]=tile[1]=tile[2]=tile[3]=top;
        tile[4]=tile[5]=tile[6]=tile[7]=0;
        VDP_loadTileData(tile,R22_PAIR_TILE_BASE+p,1,CPU);
    }
}
static void R47_ClearPairBuffer(void)
{
    uint16_t *w=(uint16_t *)(void *)r22_fb.pixels;
    for(uint16_t i=0;i<38*R22_H;i++)w[i]=(uint16_t)R22_PAIR_TILE_BASE;
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
    const uint16_t *srca=R22_PairRow(r22_fb.pixels,2);
    const uint16_t *srcb=R22_PairRow(r22_fb.pixels,3);
    uint16_t dsta=VDP_BG_A+128,dstb=VDP_BG_B+128;
    for(uint16_t y=1;y<22;y++,srca+=76,srcb+=76,dsta+=128,dstb+=128){
        uint32_t a=((uint32_t)(uintptr_t)srca)>>1;
        *ctrl=0x9300|38;*ctrl=0x9400;
        *ctrl=0x9500|(a&255);*ctrl=0x9600|((a>>8)&255);*ctrl=0x9700|((a>>16)&127);
        volatile uint32_t command=VDP_DMA_VRAM_ADDR(dsta);
        volatile uint16_t *words=(volatile uint16_t*)&command;
        *ctrl=words[0];
        __asm__ volatile("move.w %0,(%1)"::"m"(words[1]),"a"(ctrl):"cc","memory");
        if(!r22_overlay_dirty){
            a=((uint32_t)(uintptr_t)srcb)>>1;
            *ctrl=0x9300|38;*ctrl=0x9400;
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
#if defined(DOOM_R35_ART_RAW)
    if(r35_native_active>=0)
        memset(r40b_native_seen,0,R40B_OCC_BYTES);
#endif
}
static void R22_EndOverlay(void){
#if defined(DOOM_R35_ART_RAW)
    if(r35_native_active>=0){
        if(r22_overlay_dirty && !r22_text_this_frame){
            R22_ClearOverlay();
            R40B_ResetNativeText();
        } else if(r22_text_this_frame){
            R40B_PruneNativeText();
        }
        return;
    }
#endif
    if(r22_overlay_dirty && !r22_text_this_frame)R22_ClearOverlay();
}
void V_ClearViewWindow(void){
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
static void R22_Num3(uint16_t x,uint16_t y,int32_t v){if(v<0)v=0;if(v>999)v=999;char s[4]={(char)('0'+v/100),(char)('0'+v/10%10),(char)('0'+v%10),0};R22_DrawText(VDP_BG_A,s,x,y);}
static void R22_HUD(void){
    static uint16_t health=65535,armor=65535,ammo=65535;
    uint16_t h=_g_player.mo?_g_player.mo->health:_g_player.health,a=_g_player.armorpoints,b=_g_player.ammo[am_clip];
    VDP_setTextPlane(BG_A);VDP_setTextPalette(PAL0);VDP_setTextPriority(TRUE);
    if(h!=health||a!=armor||b!=ammo){
        R22_DrawText(VDP_BG_A,"HEALTH",1,23);R22_Num3(8,23,h);R22_DrawText(VDP_BG_A,"ARMOR",13,23);R22_Num3(19,23,a);
        R22_DrawText(VDP_BG_A,"BULLETS",24,23);R22_Num3(32,23,b);health=h;armor=a;ammo=b;
        R22_DrawText(VDP_BG_A,"DOOM PX4 - 76x44",1,25);
    }
    static uint32_t vb;static uint16_t frames;frames++;
    uint32_t dt=_g_vblankCount-vb;if(dt>=60){uint16_t f=(uint32_t)frames*600/dt;if(f>999)f=999;char s[8]={(char)('0'+f/100),(char)('0'+f/10%10),'.',(char)('0'+f%10),'f','p','s',0};R22_DrawText(VDP_BG_A,s,31,0);frames=0;vb=_g_vblankCount;}
}
void I_FinishUpdate(void){
#if defined(DOOM_R35_ART_RAW)
    if(r35_native_active>=0){
        if(_g_gamestate!=GS_LEVEL){
            /* R40a: This branch skips regular pixel4 presentation, but
             * must still retire the previous WINDOW overlay on frames
             * without a menu (for example, after Start closes it). */
            R22_EndOverlay();
            return; /* Native picture remains in VRAM. */
        }
        R35_LeaveNative4(); /* Gameplay uses the original p4 pipeline. */
    }
#endif
    if(r22_fb.before!=R22_GUARD||r22_fb.after!=R22_GUARD)I_Error("PX4 framebuffer guard");
    R20_StopVideo();R22_EndOverlay();
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
    __asm__ volatile("":::"memory");r22_ready=1;
#if defined(TIMEDEMO)
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
    VDP_setVerticalScroll(BG_A,0);VDP_setVerticalScroll(BG_B,-4);
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
    r22_fb.before=r22_fb.after=R22_GUARD;
#if defined(DOOM_R47_PLANE_PAIR)
    R47_ClearPairBuffer();
#else
    memset(r22_fb.pixels,0,R22_FB_BYTES);
#endif
    r22_front=0;r22_ready=0;
#if defined(DOOM_R22_PATTERN)
    for(uint16_t y=0;y<44;y++)for(uint16_t x=0;x<76;x++)R22_Put(r22_fb.pixels,x,y,(uint8_t)((x+y)&15));
    I_FinishUpdate();R20_StopVideo();VDP_setTextPlane(BG_A);R22_DrawText(VDP_BG_A,"PX4: EACH SQUARE IS 4x4",1,0);
    for(;;)SYS_doVBlankProcess();
#endif
}
void I_ShutdownGraphics(void){R20_StopVideo();}
