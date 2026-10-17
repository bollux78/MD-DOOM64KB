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
#include "r22_palette.h"
#include "r22_maps.h"
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
static volatile uint16_t r22_front;
static uint16_t r22_next_bank;
static uint32_t r22_queued;
static uint8_t r22_overlay_dirty;
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
    VDP_clearPlane(BG_B, TRUE);
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
    int16_t n=v->yh-v->yl+1;if(n<=0)return;
    uint16_t frac=(uint16_t)((v->texturemid>>7)+(v->yl-CENTERY)*v->fracstep);
    for(int16_t y=v->yl;y<=v->yh;y++) {
        uint8_t c=v->source[frac>>9];
        if(v->colormap)c=v->colormap[c];
        R22_Plot(v->x,y,r22_color[c]);frac+=v->fracstep;
    }
}
void R_DrawColumnWall(const draw_column_vars_t *v){R_DrawColumnSprite(v);}
void R_DrawFuzzColumn(const draw_column_vars_t *v){R_DrawColumnSprite(v);}
void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){
    c=r22_color[c];for(int16_t y=v->yl;y<=v->yh;y++)R22_Plot(v->x,y,c);
}
void I_ReloadPalette(void) { /* Palette tables generated from the embeddedPLAYPAL. */ }
void I_SetPalette(int8_t p){r22_newpal=p;}
void V_SetSTPalette(void){}
static void R22_Palette(int8_t p){if(p<0)p=0;if(p>13)p=13;PAL_setColors(0,r22_cram[(uint8_t)p],16,DMA);}

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
    const uint16_t *src=&r22_maps[r22_next_bank][38];
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
    if(!bus)Z80_releaseBus();
    __asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");
    r22_front=r22_next_bank;
    __asm__ volatile("":::"memory");r22_ready=0;
}
void R20_AbortVideo(void){uint16_t sr;__asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr":"=d"(sr)::"cc","memory");r22_ready=0;r22_newpal=100;__asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");}
void R20_StopVideo(void){while(r22_ready){if(_g_vblankCount-r22_queued>180)I_Error("PX4 VBlank timeout");}}

static void R22_UploadBack(uint16_t bank){
    volatile uint32_t *data=(volatile uint32_t*)0xC00000,*ctrl=(volatile uint32_t*)0xC00004;
    uint16_t tile=(uint16_t)(16+bank*R22_TILES+38);
    /* CPU conversion/writes affect only the hidden bank. Mask interrupts
       for ONE32-byte tile at a time; release between tiles for XGM/JOY.
       No68k->VDP DMA from an expanded26KB work-RAM buffer is needed. */
    for(uint16_t y=1;y<22;y++)for(uint16_t x=0;x<38;x++,tile++){
        uint32_t top=R22_ExpandPair(r22_fb.pixels[(2*y)*38+x]);
        uint32_t bottom=R22_ExpandPair(r22_fb.pixels[(2*y+1)*38+x]);
        uint16_t sr;__asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr":"=d"(sr)::"cc","memory");
        VDP_setAutoInc(2);*ctrl=VDP_WRITE_VRAM_ADDR(tile*32u);
        *data=top;*data=top;*data=top;*data=top;
        *data=bottom;*data=bottom;*data=bottom;*data=bottom;
        __asm__ volatile("move.w %0,%%sr"::"d"(sr):"cc","memory");
    }
}

static void R22_Text(int16_t x,int16_t y,const char *s){
    if(x<0||x>=38||y<0||y>=22)return;
    /* BG_B high-priority glyphs overlay the raster without a text RAM map.
       BG_B rows24..31 are reserved for zeroedSAT/HScroll (sharedFC00 base), never text. */
    VDP_setTextPlane(y==0?BG_A:BG_B);VDP_setTextPalette(PAL0);VDP_setTextPriority(TRUE);
    if(y>0)r22_overlay_dirty=1;
    char b[39];uint16_t n=0;while(s[n]&&n<(uint16_t)(38-x)){b[n]=s[n];n++;}b[n]=0;
    VDP_drawText(b,x,y);VDP_setTextPlane(BG_A);
}
void V_DrawCharacter(int16_t x,int16_t y,uint8_t c,char ch){(void)c;char b[2]={ch,0};if(ch==1||ch==2)b[0]='>';if((uint8_t)b[0]<32||(uint8_t)b[0]>127)b[0]=' ';R22_Text(x,y,b);}
void V_DrawCharacterForeground(int16_t x,int16_t y,uint8_t c,char ch){V_DrawCharacter(x,y,c,ch);}
void V_DrawSTCharacter(int16_t x,int16_t y,uint8_t c,char ch){V_DrawCharacter(x,y,c,ch);}
void V_DrawString(int16_t x,int16_t y,uint8_t c,const char *s){(void)c;R22_Text(x,y,s);}
void V_DrawSTString(int16_t x,int16_t y,uint8_t c,const char *s){V_DrawString(x,y,c,s);}
void V_ClearString(int16_t y,size_t n){for(uint16_t x=0;x<n&&x<38;x++)V_DrawCharacter(x,y,0,' ');}
void R22_BeginFrame(void){
    if(r22_overlay_dirty){R20_StopVideo();VDP_clearPlane(BG_B,TRUE);r22_overlay_dirty=0;}
}
void V_ClearViewWindow(void){memset(r22_fb.pixels,0,R22_FB_BYTES);VDP_clearPlane(BG_B,TRUE);r22_overlay_dirty=0;}
void V_DrawBackground(int16_t n){(void)n;V_ClearViewWindow();}
void V_DrawRawFullScreen(int16_t n){
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
static void R22_Num3(uint16_t x,uint16_t y,int32_t v){if(v<0)v=0;if(v>999)v=999;char s[4]={(char)('0'+v/100),(char)('0'+v/10%10),(char)('0'+v%10),0};VDP_drawText(s,x,y);}
static void R22_HUD(void){
    static uint16_t health=65535,armor=65535,ammo=65535;
    uint16_t h=_g_player.mo?_g_player.mo->health:_g_player.health,a=_g_player.armorpoints,b=_g_player.ammo[am_clip];
    VDP_setTextPlane(BG_A);VDP_setTextPalette(PAL0);VDP_setTextPriority(TRUE);
    if(h!=health||a!=armor||b!=ammo){
        VDP_drawText("HEALTH",1,23);R22_Num3(8,23,h);VDP_drawText("ARMOR",13,23);R22_Num3(19,23,a);
        VDP_drawText("BULLETS",24,23);R22_Num3(32,23,b);health=h;armor=a;ammo=b;
        VDP_drawText("DOOM PX4 - 76x44",1,25);
    }
    static uint32_t vb;static uint16_t frames;frames++;
    uint32_t dt=_g_vblankCount-vb;if(dt>=60){uint16_t f=(uint32_t)frames*600/dt;if(f>999)f=999;char s[8]={(char)('0'+f/100),(char)('0'+f/10%10),'.',(char)('0'+f%10),'f','p','s',0};VDP_drawText(s,31,0);frames=0;vb=_g_vblankCount;}
}
void I_FinishUpdate(void){
    if(r22_fb.before!=R22_GUARD||r22_fb.after!=R22_GUARD)I_Error("PX4 framebuffer guard");
    R20_StopVideo();
#if defined(DOOM_R20_STACKGUARD)
    static uint8_t sample;R20_PROBE();if((sample++&15u)==0)R20_DiagSample();
#endif
    uint16_t back=r22_front^1;R22_UploadBack(back);
    if(_g_gamestate==GS_LEVEL)R22_HUD();
    r22_next_bank=back;r22_queued_pal=r22_newpal;r22_newpal=100;r22_queued=_g_vblankCount;
    __asm__ volatile("":::"memory");r22_ready=1;
#if defined(TIMEDEMO)
    I_BenchmarkFrame();
#endif
}
void I_InitGraphicsHardwareSpecificCode(void){
    R20_StopVideo();VDP_setScreenWidth320();VDP_setPlaneSize(64,32,FALSE);
    /* All map/table addresses>=E000, soSGDK relocates its96font tiles to
       D400..DFFF, above both graphics banks (endingD2FF). */
    VDP_setBGBAddress(0xF000);VDP_setWindowAddress(0xF000);VDP_setSpriteListAddress(0xFC00);VDP_setHScrollTableAddress(0xFC00);VDP_setBGAAddress(0xE000);
    VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,0);
    if(TILE_FONT_INDEX!=1696)I_Error("PX4 font layout %u",(unsigned)TILE_FONT_INDEX);
    VDP_clearPlane(BG_A,TRUE);VDP_clearPlane(BG_B,TRUE);
    VDP_setHorizontalScroll(BG_A,0);VDP_setHorizontalScroll(BG_B,0);VDP_setVerticalScroll(BG_A,0);VDP_setVerticalScroll(BG_B,0);
    R22_InitOpenings();R22_Palette(0);r22_newpal=100;
    r22_fb.before=r22_fb.after=R22_GUARD;memset(r22_fb.pixels,0,R22_FB_BYTES);
    r22_front=0;r22_ready=0;
#if defined(DOOM_R22_PATTERN)
    for(uint16_t y=0;y<44;y++)for(uint16_t x=0;x<76;x++)R22_Put(r22_fb.pixels,x,y,(uint8_t)((x+y)&15));
    I_FinishUpdate();R20_StopVideo();VDP_setTextPlane(BG_A);VDP_drawText("PX4: EACH SQUARE IS 4x4",1,0);
    for(;;)SYS_doVBlankProcess();
#endif
}
void I_ShutdownGraphics(void){R20_StopVideo();}
void I_InitGraphics(void){I_InitGraphicsHardwareSpecificCode();isGraphicsModeSet=true;}
