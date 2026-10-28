#!/usr/bin/env python3
"""Compile actual reference/candidate column functions; compare complete buffers.
The host stand-in for R60_WallColumn models its index/fraction ADDX scheme.
Real assembly is then checked by the same-job BlastEm framebuffer comparison.
"""
from pathlib import Path
import argparse,importlib.util,subprocess,tempfile,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lab'))
import apply_r80_performance as R80
import apply_r83 as R83

def sprite(s):return R83.region(s,R83.SPRITE,'/* R42 Q2:')[2]
def wall(s):return R83.region(s,R83.WALL,'void R_DrawColumnWall(')[2]
HEADER=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#define DOOM_R47_PLANE_PAIR 1
#define DOOM_R48_PAIR_V 1
#define DOOM_R48_V_FAST 1
#define DOOM_R47_SPRITE_HOIST 1
#define DOOM_R52_CPLUT 1
#define DOOM_R60_PAIR_ASM 1
#define DOOM_R64A_PROLOGUE 1
#define DOOM_R57_CROP16 1
#define DOOM_R57_VIEW_MENU 1
#define GS_LEVEL 1
static int _g_gamestate=1;
#define R57_CROP_ACTIVE 1
#define R57_XMIN (context.xmin)
#define R57_XEND (context.xend)
#define R57_YMIN (context.border)
#define R57_YEND (context.yend)
#define R22_W 76
#define R22_H 44
#define R22_PITCH 76
#define R48_COUNT(a,b) ((void)0)
static const int16_t CENTERY=22;
typedef struct {int16_t x,yl,yh;int32_t texturemid;uint16_t fracstep;const uint8_t *source,*colormap;} draw_column_vars_t;
typedef struct {int16_t border,xmin,xend,yend;} r64a_ctx_t;
static r64a_ctx_t context;
static const r64a_ctx_t *R64A_Get(r64a_ctx_t *tmp){(void)tmp;return &context;}
static uint8_t r22_color[256],oddmap[256],comp[256],source[128],cmap[256];
static struct{const uint8_t *wall_even,*wall_odd;} R59_CURRENT={r22_color,oddmap};
static int fast;
static const uint8_t *R52_LUT(const uint8_t *map,uint16_t parity){(void)parity;return fast&&map?comp:0;}
static const uint8_t *R64A_LUT(const r64a_ctx_t *cx,const uint8_t *map,uint16_t parity){(void)cx;return R52_LUT(map,parity);}
static struct {uint32_t before;uint8_t pixels[3344];uint32_t after;} r22_fb;
static uint8_t *R22_PixelByte(uint8_t *p,uint16_t x,uint16_t y){return p+(y>>1)*152+(x&1)*76+(x>>1)*2+1;}
static uint8_t tex(const uint8_t *s,const uint8_t *m,uint16_t *idx,uint16_t *lo,uint16_t istep,uint16_t lstep){
 uint8_t c=m[s[*idx]];uint32_t sum=(uint32_t)*lo+lstep;
 *lo=(uint16_t)sum;*idx=(uint16_t)((*idx+istep+(sum>>16))&127u);return c;
}
static void R60_WallDraw(uint8_t *d,const uint8_t *s,const uint8_t *m,uint16_t f,uint16_t step,uint16_t count,uint16_t odd){
 uint16_t idx=f>>9,lo=(uint16_t)(f<<7),is=step>>9,ls=(uint16_t)(step<<7);
 if(odd&&count){uint8_t c=tex(s,m,&idx,&lo,is,ls);*d=(uint8_t)((*d&240)|c);d+=152;if(!--count)return;}
 uint16_t tail=count&1u,pairs=count>>1;
 while(pairs--){uint8_t a=tex(s,m,&idx,&lo,is,ls),b=tex(s,m,&idx,&lo,is,ls);*d=(uint8_t)((a<<4)|b);d+=152;}
 if(tail){uint8_t c=tex(s,m,&idx,&lo,is,ls);*d=(uint8_t)((*d&15)|(c<<4));}
}
'''
MAIN=r'''
static uint32_t rnd=0x12345678;
static uint32_t random32(void){rnd=rnd*1664525u+1013904223u;return rnd;}
static void reset(uint8_t seed){r22_fb.before=0x2244AA55;r22_fb.after=0x2244AA55;for(int i=0;i<3344;i++)r22_fb.pixels[i]=(uint8_t)(i*13+seed);}
static int check(draw_column_vars_t *v,unsigned trial){
 uint8_t ref[3344];uint8_t seed=(uint8_t)trial;
 reset(seed);RefSprite(v);memcpy(ref,r22_fb.pixels,3344);
 reset(seed);OptSprite(v);
 if(memcmp(ref,r22_fb.pixels,3344)||r22_fb.before!=0x2244AA55||r22_fb.after!=0x2244AA55){printf("SPR mismatch %u x%d y%d..%d step%u fast%d\n",trial,v->x,v->yl,v->yh,v->fracstep,fast);return 1;}
 reset(seed);RefWall(v);memcpy(ref,r22_fb.pixels,3344);
 reset(seed);OptWall(v);
 if(memcmp(ref,r22_fb.pixels,3344)||r22_fb.before!=0x2244AA55||r22_fb.after!=0x2244AA55){printf("WALL mismatch %u x%d y%d..%d step%u\n",trial,v->x,v->yl,v->yh,v->fracstep);return 1;}
 return 0;
}
int main(void){
 for(int i=0;i<256;i++){r22_color[i]=random32()>>28;oddmap[i]=random32()>>28;comp[i]=random32()>>28;cmap[i]=random32()>>24;}
 for(int i=0;i<128;i++)source[i]=random32()>>24;
 draw_column_vars_t v={0,0,43,0,0,source,0};unsigned trial=0;
 context=(r64a_ctx_t){6,6,72,40};
 /* Every screen coordinate/count, including odd head and clipped tail. */
 for(int x=-1;x<=76;x++)for(int y=-2;y<=44;y++)for(int count=0;count<=44;count++){
  v.x=x;v.yl=y;v.yh=y+count-1;v.texturemid=(int32_t)random32();v.fracstep=random32();fast=trial&1;v.colormap=(trial&2)?cmap:0;
  if(check(&v,trial++))return 1;
 }
 /* Bounds/context and fraction extremes; keep reference arithmetic defined. */
 for(int i=0;i<120000;i++){
  int mode=i%6;_g_gamestate=mode?1:0;
  context=(r64a_ctx_t){mode?2+mode*2:0,mode?2+mode*2:0,mode?76-mode*2:32767,mode?44-mode*2:32767};
  v.x=(int16_t)random32();v.yl=(int16_t)(random32()%30001)-15000;v.yh=(int16_t)(random32()%30001)-15000;
  v.texturemid=(int32_t)random32();v.fracstep=(uint16_t)random32();fast=i&1;v.colormap=(i&2)?cmap:0;
  if(i%4==0){v.x=random32()%76;v.yl=-(random32()%80);v.yh=random32()%100;}
  if(check(&v,trial++))return 1;
 }
 /* Full signed x domain for each supported context interval. */
 for(int mode=0;mode<8;mode++)for(int x=INT16_MIN;x<=INT16_MAX;x++){
  int xmin=mode*2,xend=mode?76-mode*2:32767,end=xend<76?xend:76;
  int old=(uint16_t)x<76 && x<xend && x>=xmin;
  int now=(uint16_t)(x-xmin)<(uint16_t)(end-xmin);
  if(old!=now)return 2;
 }
 printf("PASS %u actual sprite+wall column pairs; complete framebuffer/guards, colormap fallback, odd heads/tails, signed clipping bounds\n",trial);
 return 0;
}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--src',default=str(ROOT/'src'));a=p.parse_args()
 s=(Path(a.src)/'r22_video.inc').read_text()
 if 'DOOM_R80_PIXOFS' not in s:s=R80.apply_text(s)
 if 'R80-F1' not in s:s=R80.apply_f1(s)
 spr=R83.apply_sprite(s);clip=R83.apply_wall(s)
 assert wall(s)==wall(spr),'sprite candidate touched walls'
 assert sprite(s)==sprite(clip),'wall candidate touched sprites'
 for f,t in ((R83.apply_sprite,spr),(R83.apply_wall,clip)):
  try:f(t)
  except AssertionError:pass
  else:raise AssertionError('double apply accepted')
 code=HEADER+R80.block()+sprite(s).replace('R_DrawColumnSprite','RefSprite')+sprite(spr).replace('R_DrawColumnSprite','OptSprite')+wall(s).replace('R42_DrawPackedWall','RefWall')+wall(clip).replace('R42_DrawPackedWall','OptWall')+MAIN
 with tempfile.TemporaryDirectory() as t:
  c=Path(t)/'test.c';c.write_text(code);exe=Path(t)/'test'
  subprocess.run(['cc','-std=c11','-O2','-Wall','-Werror','-Wno-unused-variable','-fsanitize=undefined',str(c),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
 print('PASS independent scope, unique anchors, R82 fallback and double-apply guards')
if __name__=='__main__':main()
