#!/usr/bin/env python3
"""Compile the actual packed raster functions and verify scalar sampling,
clipping, framebuffer guards, column culling and Pair-V DMA source bounds.
"""
from pathlib import Path
import subprocess,tempfile,re
r=Path(__file__).resolve().parents[2]
def function(src,name):
    start=re.search(r'\b'+name+r'\s*\(',src).start()
    start=src.rfind('\n',0,start)+1
    begin=src.index('{',start);depth=1;end=begin+1
    while depth:
        depth+=(src[end]=='{')-(src[end]=='}');end+=1
    return src[start:end]
video=(r/'src/r22_video.inc').read_text();draw=(r/'src/r_draw.c').read_text()
funcs='\n'.join(function(video,n) for n in ('R_DrawColumnFlat','R_DrawColumnSprite','R42_DrawPackedWall'))
funcs+='\n'+function(draw,'R_ClearClipSegs')
funcs+='\n'+function(draw,'R_ClearOpeningClippingDetermination')
code=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>

#include "r22_pixel4.h"
#include "r57_viewport.h"
#define VIEWWINDOWWIDTH 76
#define VIEWWINDOWHEIGHT 44
#define CENTERY 22
#define GS_LEVEL 1
#define R48_COUNT(a,b) ((void)0)
#define R68_HIT(k) ((void)0)
static int _g_gamestate;
#if defined(DOOM_R57_VIEW_MENU)
R57ViewConfig r57_view;
#endif
#if defined(DOOM_R57_SIZE_MENU)
uint8_t r57_crop_enabled=1;
#endif
static uint8_t r22_color[256],r56_flat_even[256],r56_flat_odd[256];
static uint8_t r56_wall_even[256],r56_wall_odd[256];
static uint8_t solidcol[76];
static int16_t floorclip[76],ceilingclip[76];
static struct { uint8_t before[16];uint8_t pixels[R22_FB_BYTES];uint8_t after[16];} r22_fb;
typedef struct {int16_t x,yl,yh;uint16_t fracstep;int32_t texturemid;
const uint8_t *source,*colormap;} draw_column_vars_t;
'''+funcs+r'''
static uint32_t rng=123456;
static uint32_t rnd(void){rng=rng*1664525u+1013904223u;return rng;}
static unsigned argnum(const char *s){unsigned n=0;while(*s)n=n*10+(*s++-'0');return n;}
int main(int argc,char **argv){
#if defined(DOOM_R57_VIEW_MENU)
 assert(argc==4);r57_view=R57_ViewMake(argnum(argv[1]),argnum(argv[2]),argnum(argv[3]));
#endif
#if defined(DOOM_R57_SIZE_MENU)
 r57_crop_enabled=(argc>1 && argv[1][0]=='1');
#endif
 uint8_t source[128],cm[256];
 for(int i=0;i<256;i++){
  cm[i]=(i*7u+3u)&255;
  r22_color[i]=r56_flat_even[i]=r56_wall_even[i]=(i%15)+1;
  r56_flat_odd[i]=r56_wall_odd[i]=((i*3)%15)+1;
 }
 for(int i=0;i<128;i++)source[i]=i*11u;
 for(int state=0;state<2;state++){
  _g_gamestate=state;
  #if defined(DOOM_R57_VIEW_MENU)
  const int trials=184;
#else
  const int trials=1200;
#endif
  for(int trial=0;trial<trials;trial++){
   memset(&r22_fb,0xa5,sizeof(r22_fb));memset(r22_fb.pixels,0,R22_FB_BYTES);
   draw_column_vars_t v={(int16_t)((int)(rnd()%92)-8),
      (int16_t)((int)(rnd()%55)-10),0,(uint16_t)(rnd()%4000),
      (int32_t)(rnd()%500000),source,(trial&1)?cm:0};
   v.yh=v.yl+(rnd()%60);int kind=trial%3;int flat=kind==0;uint8_t color=rnd();
   if(flat)R_DrawColumnFlat(color,&v);else if(kind==1)R_DrawColumnSprite(&v);else R42_DrawPackedWall(&v);
   for(int y=0;y<44;y++)for(int x=0;x<76;x++){
    int inside=x==v.x && y>=v.yl && y<=v.yh;
    if(state){
#ifdef DOOM_R57_CROP16
     inside=inside && (!R57_CROP_ACTIVE ? (x>=2 && y>=2) : (x>=R57_XMIN && x<R57_XEND && y>=R57_YMIN && y<R57_YEND));
#else
     inside=inside && x>=2 && y>=2;
#endif
    }
    uint8_t expect=0;
    if(inside){
     uint8_t ci=color;
     if(!flat){uint16_t f=(uint16_t)((v.texturemid>>7)+(v.yl-CENTERY)*v.fracstep);
       f=(uint16_t)(f+(uint32_t)(y-v.yl)*v.fracstep);ci=source[f>>9];
       if(v.colormap)ci=cm[ci];}
     expect=(x&1)?r56_wall_odd[ci]:r56_wall_even[ci];
    }
    uint8_t got=*R22_PixelByte(r22_fb.pixels,x,y);
    got=(y&1)?(got&15):(got>>4);
    assert(got==expect);
   }
   for(int i=0;i<16;i++)assert(r22_fb.before[i]==0xa5 && r22_fb.after[i]==0xa5);
  }
 }
 R_ClearClipSegs();R_ClearOpeningClippingDetermination();
 for(int x=0;x<76;x++){
#ifdef DOOM_R57_CROP16
  assert(solidcol[x]==(R57_CROP_ACTIVE ? (x<R57_XMIN || x>=R57_XEND) : (x==0)));
  assert(floorclip[x]==(R57_CROP_ACTIVE?R57_YEND:44) && ceilingclip[x]==(R57_CROP_ACTIVE?R57_YMIN-1:0));
#else
  assert(solidcol[x]==(x==0));assert(floorclip[x]==44 && ceilingclip[x]==0);
#endif
 }
#ifdef DOOM_R57_CROP16
 assert(R57_DMA_WORDS==(R57_XEND-R57_XMIN)/2);
 for(int y=R57_TILE_YMIN;y<R57_TILE_YEND;y++)for(int p=0;p<2;p++){
  int offset=y*152+p*76+R57_TILE_XMIN*2;
  assert(offset>=0 && offset+R57_DMA_WORDS*2<=R22_FB_BYTES);
  for(int x=R57_TILE_XMIN;x<R57_TILE_XEND;x++)for(int yy=0;yy<2;yy++){
   uint8_t *ptr=R22_PixelByte(r22_fb.pixels,x*2+p,y*2+yy);
   assert(ptr==r22_fb.pixels+y*152+p*76+x*2+1);
  }
 }
#endif
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    p=Path(td);(p/'oracle.c').write_text(code)
    for crop,extra in ((False,[]),(True,[]),(True,['-DDOOM_R57_NARROW256']),(True,['-DDOOM_R57_SIZE_MENU']),(True,['-DDOOM_R57_VIEW_MENU'])):
        flags=['-DDOOM_R22_PIXEL4','-DDOOM_R48_PAIR_V','-DDOOM_R47_PLANE_PAIR',
               '-DDOOM_R47_FLAT_HOIST','-DDOOM_R47_SPRITE_HOIST','-DDOOM_R48_V_FAST',
               '-DDOOM_R56_DUAL_COLOR','-DDOOM_R11_LEFTCOL_CLIP','-DDOOM_R11_TOPBAR_CLIP']
        if crop:flags+=['-DDOOM_R57_CROP16']
        flags+=extra
        subprocess.run(['gcc','-std=c99','-O1','-g','-fsanitize=undefined',*flags,
                        '-I',str(r/'src'),str(p/'oracle.c'),'-o',str(p/'oracle')],check=True)
        
        if '-DDOOM_R57_VIEW_MENU' in extra:
            for mode in (0,1):
                for h in (0,8,16,24,32):
                    for v in (0,8,16,24,32):
                        subprocess.run([str(p/'oracle'),str(mode),str(h),str(v)],check=True)
            print('PASS all 50 runtime mode / horizontal crop / vertical crop combinations')
        else:
            for mode in ('0','1') if '-DDOOM_R57_SIZE_MENU' in extra else ('1',):
                subprocess.run([str(p/'oracle'),mode],check=True)
        print('PASS actual raster scalar equivalence, level/nonlevel, 2400 randomized columns, guards, culling, DMA bounds:', 'crop16' if crop else 'full')
