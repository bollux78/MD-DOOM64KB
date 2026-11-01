#!/usr/bin/env python3
"""Exercise production cell8 writers against independent four-sample Pair-V writes."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
code=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
enum { GS_LEVEL=1 };
int _g_gamestate;
const int16_t CENTERY=11;
struct { uint8_t xmin,xend,ymin,yend; } r57_view;
typedef struct { int16_t x,yl,yh; uint16_t fracstep; int32_t texturemid;
                 const uint8_t *source,*colormap; } draw_column_vars_t;
#include "r105_cell8.h"
static uint32_t rng=105;
static uint32_t next(void){rng=rng*1664525u+1013904223u;return rng;}
static int visible(int x,int y){return x>=0&&x<38&&y>=0&&y<22&&
 (_g_gamestate!=GS_LEVEL||(2*x>=r57_view.xmin&&2*x<r57_view.xend&&2*y>=r57_view.ymin&&2*y<r57_view.yend));}
static void put(uint8_t *p,unsigned x,unsigned y,uint8_t c){
 unsigned i=(y/2)*152+(x%2)*76+(x/2)*2+1;
 if(y%2)p[i]=(p[i]&240)|(c&15);else p[i]=(p[i]&15)|((c&15)<<4);
}
static void ref(uint8_t *p,int x,int y,uint8_t a,uint8_t b){
 put(p,2*x,2*y,a);put(p,2*x,2*y+1,a);put(p,2*x+1,2*y,b);put(p,2*x+1,2*y+1,b);
}
int main(void){
 uint8_t out[3344+32],expected[3344+32],src[128],a[256],b[256],cm[256];
 for(unsigned i=0;i<256;i++){a[i]=(i*3+7)&15;b[i]=(i*5+2)&15;cm[i]=(i*17+11)&255;}
 for(unsigned i=0;i<128;i++)src[i]=i*37;
 for(unsigned k=0;k<30000;k++){
  for(unsigned i=0;i<sizeof out;i++)out[i]=expected[i]=next()>>24;
  _g_gamestate=k%3==0?0:GS_LEVEL;
  unsigned h=(k%5)*8,v=((k/5)%5)*8,m=(k/25)%2;
  r57_view.xmin=(m?6:2)+h/4;r57_view.xend=(m?70:76)-h/4;
  r57_view.ymin=2+v/4;r57_view.yend=44-v/4;
  draw_column_vars_t d={(int)(next()%44)-3,(int)(next()%34)-6,(int)(next()%34)-6,
   next()&65535,(int32_t)(next()%2000000)-1000000,src,k%2?cm:0};
  R105_CellTexture(out+16,&d,a,b,d.colormap);
  uint16_t f=(uint16_t)((d.texturemid>>7)+(d.yl-CENTERY)*d.fracstep);
  for(int y=d.yl;y<=d.yh;y++,f=(uint16_t)(f+d.fracstep))if(visible(d.x,y)){
   uint8_t c=src[f>>9];if(d.colormap)c=cm[c];ref(expected+16,d.x,y,a[c],b[c]);
  }
  assert(!memcmp(out,expected,sizeof out));
  int16_t y0=d.yl,y1=d.yh;
  if(R105_CellClip(d.x,&y0,&y1)){
   uint8_t ca=next(),cb=next();R105_CellFill(out+16,d.x,y0,y1,ca,cb);
   for(int y=d.yl;y<=d.yh;y++)if(visible(d.x,y))ref(expected+16,d.x,y,ca,cb);
   assert(!memcmp(out,expected,sizeof out));
  }
 }
 for(int y=-2;y<24;y++)for(int x=-2;x<40;x++)assert(!!R105_CellVisible(x,y)==!!visible(x,y));
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    c=Path(td)/'cell8.c'; c.write_text(code)
    subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-fsanitize=undefined',
                    '-I',str(root/'scripts/lab/cell8'),str(c),'-o',str(c.with_suffix(''))],check=True)
    subprocess.run([str(c.with_suffix(''))],check=True)
print('PASS 30,000 clipped texture/fill cases, both LUTs, all crop sizes/H32/H40, canaries and attributes')
