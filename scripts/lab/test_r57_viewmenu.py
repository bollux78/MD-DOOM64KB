#!/usr/bin/env python3
"""Exercise actual menu setter and video-mode switch with queued-DMA mocks."""
from pathlib import Path
import re,subprocess,tempfile
r=Path(__file__).resolve().parents[2];s=(r/'src/r22_video.inc').read_text()
def function(name):
 a=re.search(r'\b'+name+r'\s*\(',s).start();a=s.rfind('\n',0,a)+1
 b=s.index('{',a);depth=1;e=b+1
 while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
code=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "r57_viewport.h"
#define GS_LEVEL 1
#define FALSE 0
#define TRUE 1
#define BG_A 0
#define BG_B 1
#define WINDOW 2
R57ViewConfig r57_view;
static R57ViewConfig queued;
static int pending,waits,enabled=1,hardware_width=320,scroll[2]={0,4},cleared;
static uint8_t r57_was_level,r57_h32_active,r57_hud_dirty,r22_overlay_dirty;
static int _g_gamestate,_g_menuactive,_g_demoplayback;
void R20_StopVideo(void){if(pending)assert(memcmp(&queued,&r57_view,sizeof(queued))==0);pending=0;}
void VDP_setEnable(int v){assert(!pending);enabled=v;}
void VDP_waitDMACompletion(void){assert(!pending);waits++;}
void VDP_setScreenWidth256(void){assert(!enabled);hardware_width=256;}
void VDP_setScreenWidth320(void){assert(!enabled);hardware_width=320;}
void VDP_clearPlane(int plane,int dma){assert(!enabled && dma==TRUE);cleared|=1<<plane;}
void VDP_setHorizontalScroll(int plane,int value){assert(!enabled);scroll[plane]=value;}
'''+function('R57_ChangeView')+'\n'+function('R57_VideoMode')+r'''
static void geometry(void){
 assert(r57_view.mode<=1 && r57_view.hcrop<=32 && r57_view.vcrop<=32);
 assert((r57_view.xend-r57_view.xmin)*4==(r57_view.mode?256:296)-r57_view.hcrop*2);
 assert((r57_view.yend-r57_view.ymin)*4==168-r57_view.vcrop*2);
 assert(r57_view.xmin>=2 && r57_view.xend<=76 && r57_view.ymin>=2 && r57_view.yend<=44);
 assert(!(r57_view.xmin&1) && !(r57_view.xend&1) && !(r57_view.ymin&1) && !(r57_view.yend&1));
}
int main(void){
 for(int mode=0;mode<2;mode++)for(int h=0;h<=32;h+=8)for(int v=0;v<=32;v+=8){
  r57_view=R57_ViewMake(mode,h,v);geometry();
  for(int field=0;field<3;field++)for(int right=0;right<2;right++){
   r57_view=R57_ViewMake(mode,h,v);queued=r57_view;pending=1;r57_was_level=1;
   R57_ChangeView(field,right);assert(!pending && !r57_was_level);geometry();
   assert(r57_view.mode==(field==0?!mode:mode));
   assert(r57_view.hcrop==(field==1?(h+(right?8:32))%40:h));
   assert(r57_view.vcrop==(field==2?(v+(right?8:32))%40:v));
  }
 }
 for(int mode=0;mode<2;mode++)for(int level=0;level<2;level++)for(int menu=0;menu<2;menu++)for(int demo=0;demo<2;demo++){
  r57_view=R57_ViewMake(mode,16,32);_g_gamestate=level;_g_menuactive=menu;_g_demoplayback=demo;
  int desired=mode && level && !menu;
  /* Force both transition directions, after the old frame is retired. */
  r57_h32_active=!desired;queued=r57_view;pending=1;R20_StopVideo();cleared=0;
  R57_VideoMode();
  assert(enabled && r57_h32_active==desired && hardware_width==(desired?256:320));
  assert(scroll[0]==(desired?-24:0) && scroll[1]==(desired?-20:4));
  assert(cleared==7 && r57_hud_dirty && !r57_was_level && !r22_overlay_dirty);
  int before=waits;R57_VideoMode();assert(waits==before); /* stable mode adds no VDP writes */
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['gcc','-O1','-std=c99','-fsanitize=undefined','-fno-sanitize-recover=undefined',
  '-DDOOM_R22_PIXEL4','-DDOOM_R48_PAIR_V','-DDOOM_R47_PLANE_PAIR','-DDOOM_R57_CROP16',
  '-DDOOM_R57_VIEW_MENU','-I',str(r/'src'),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS actual menu setter: 300 queued-frame crop/mode changes, 50 geometries; 32 actual H32/H40/menu/demo transitions and stable-mode no-op checks')
