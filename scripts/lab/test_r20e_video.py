#!/usr/bin/env python3
"""Compile actual video functions in a host harness and compare RAM/VRAM frames.
SGDK DMA/font/palette services are stubs; tests state/invalidation behavior,
not physical VDP timing or the compiled 68000 executable.
"""
import pathlib,re,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[2]
src=(root/'src/i_genesisv.c').read_text()
def function(name):
    m=re.search(r'(?:static )?(?:void|uint16_t) '+name+r'\([^\n]*\)\n\{',src)
    assert m,name
    start=m.start();at=m.end()-1;depth=0
    # These selected functions have balanced braces in CPP branches/comments.
    for i in range(at,len(src)):
        if src[i]=='{':depth+=1
        elif src[i]=='}':
            depth-=1
            if depth==0:return src[start:i+1]
    raise AssertionError(name)
a=src.index('#if defined(DOOM_R20_HUD_LAZY)\nstatic uint8_t');b=src.index('#define HUD_COL 15',a)
code=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#define VIEWWINDOWWIDTH 38
#define VIEWWINDOWHEIGHT 22
#define VDP_DISPLAY_ROWS 28
#define SCREENWIDTH 320
#define SCREENHEIGHT 200
#define FRACBITS 16
#define BLACK_CELL 0
#define HUD_COL 15
#define GS_LEVEL 1
#define BG_A 0
#define DMA 1
#define CPU 0
#define am_clip 0
#define DOOM_CLASSIC_TEXT_HUD 1
#define DOOM_HUD_DMA_STATUS_ONLY 1
#define DOOM_R11_TOPBAR_CLIP 1
#define DOOM_R11_LEFTCOL_CLIP 1
#define DOOM_NO_VSYNC 1
typedef int32_t fixed_t;
static uint16_t _s_screen[38*28],vram[38*28],colorcell[256];
static uint32_t _g_vblankCount;
static int _g_gamestate;
struct object {int32_t health;};
static struct object mo;
static struct {struct object *mo;int32_t health,armorpoints,ammo[1];} _g_player;
static uint16_t font_cell(uint8_t color,char c) {(void)color;return 0x8000|(uint8_t)c;}
#define NO_PALETTE_CHANGE 100
static int8_t newpal=NO_PALETTE_CHANGE;
static void I_UploadNewPalette(int8_t p) {(void)p;}
static uint8_t picture[320*200];
static const uint8_t *W_GetLumpByNum(int16_t n) {(void)n;return picture;}
static void VDP_setTileMapDataRect(int plane,const uint16_t *source,int x,int y,int w,int h,int stride,int mode) {
 (void)plane;(void)mode;
 if(x<0||y<0||x+w>38||y+h>28)abort();
 for(int r=0;r<h;r++)for(int c=0;c<w;c++)vram[(y+r)*38+x+c]=source[r*stride+c];
}
'''
code+=src[a:b]
for name in ['hud_putc','hud_num','hud_label','hud_saturate3','I_DrawClassicTextHUD','I_DrawDebugCounters','I_FinishUpdate','V_DrawRawFullScreen','V_DrawBackground','V_ClearViewWindow','V_DrawCharacter','V_DrawString','V_ClearString']:
    code+=function(name)+'\n'
code+=r'''
static uint32_t seed=20261017u;
static uint32_t rnd(void){seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;return seed;}
int main(void){
 for(int i=0;i<256;i++)colorcell[i]=(uint16_t)(i+1);
 for(int i=0;i<320*200;i++)picture[i]=(uint8_t)i;
 R20_InvalidateVideo();
 for(int frame=0;frame<1000;frame++){
   if(frame%97==0)_g_gamestate=0;
   if(frame%97==9)_g_gamestate=GS_LEVEL;
   if(frame%13==0)mo.health=(int32_t)(rnd()%1500)-50;
   if(frame%29==0)_g_player.armorpoints=(int32_t)(rnd()%1100)-20;
   if(frame%5==0)_g_player.ammo[0]=(int32_t)(rnd()%1300)-10;
   _g_player.health=mo.health+3;
   _g_player.mo=frame%31==0?NULL:&mo;
   _g_vblankCount+=1+rnd()%25;
   if(frame%17==0)V_ClearViewWindow();
   if(frame%41==0)V_DrawRawFullScreen(0);
   if(frame%53==0)V_DrawBackground(0);
   /* Normal renderer touches only the clipped viewport, not the HUD. */
   for(int y=1;y<22;y++)for(int x=1;x<38;x++)_s_screen[y*38+x]=(uint16_t)(frame+y+x);
   if(frame%11==0)V_DrawString(0,0,0,"message");
   if(frame%19==0)V_DrawString(30,0,0,"overwrite FPS");
   if(frame%23==0)V_ClearString(0,38);
   if(frame%37==0)V_DrawCharacter(33,0,0,'X');
   I_FinishUpdate();
   if(fwrite(_s_screen,sizeof(_s_screen),1,stdout)!=1)return 2;
   if(fwrite(vram,sizeof(vram),1,stdout)!=1)return 3;
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=pathlib.Path(tmp);c=p/'video.c';c.write_text(code)
    reference=None
    for name,flags in [('control',[]),('hud',['-DDOOM_R20_HUD_LAZY']),('fps',['-DDOOM_R20_FPS_LAZY']),('both',['-DDOOM_R20_HUD_LAZY','-DDOOM_R20_FPS_LAZY'])]:
        exe=p/name
        subprocess.run(['gcc','-O2','-std=c11',*flags,str(c),'-o',str(exe)],check=True)
        output=subprocess.check_output([str(exe)])
        if reference is None:reference=output
        else:
            if output!=reference:
                index=next(i for i,(a,b) in enumerate(zip(output,reference)) if a!=b)
                raise AssertionError((name,'frame',index//(38*28*2*2),'byte',index))
        print(f'PASS video {name}: 1000 RAM+VRAM frames, clears/text/state/player transitions')
