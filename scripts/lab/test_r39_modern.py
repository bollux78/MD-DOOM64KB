#!/usr/bin/env python3
"""Tile-word oracle: full R39 palette/index bits, clipping, phase and untouched words."""
from pathlib import Path
import subprocess,tempfile,sys
r=Path(__file__).resolve().parents[2]
if '--source' in sys.argv:
    v=(r/'src/r22_video.inc').read_text();m=(r/'src/m_text.c').read_text()
    assert '#include "r39m_scene.inc"' in v
    assert 'genpal_cram[(uint8_t)p],64,CPU' in v
    assert 'src+y*38u+r92_rect.x0' in v
    assert '{2,"Shadow:"' not in m and '{2,"Color mode:"' not in m
    assert 'r39f_mode_names' in m and 'Dithering:' in m
    assert 'r104_sr' in (r/'src/r22_blocklinks.h').read_text()
    print('PASS R39 original colour path, one word/tile DMA, tri-dither menu, protected SRAM')
    sys.exit()
code=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
enum{GS_LEVEL=1};int _g_gamestate;const int16_t CENTERY=11;
struct{uint8_t xmin,xend,ymin,yend;}r57_view;
typedef struct{int16_t x,yl,yh;uint16_t fracstep;int32_t texturemid;const uint8_t *source,*colormap;}draw_column_vars_t;
#include "r39m_draw.h"
static uint32_t seed=39;
static uint32_t rnd(void){seed=seed*1664525u+1013904223u;return seed;}
static int vis(int x,int y){return x>=0&&x<38&&y>=0&&y<22&&(_g_gamestate!=GS_LEVEL||
 (2*x>=r57_view.xmin&&2*x<r57_view.xend&&2*y>=r57_view.ymin&&2*y<r57_view.yend));}
int main(void){
 uint16_t actual[1672+16],expected[1672+16],maps[256],colors[256];uint8_t src[128],shade[256];
 for(unsigned i=0;i<256;i++){maps[i]=((i%4)<<13)|(16+i%226);colors[i]=(((i+1)%4)<<13)|(16+(i*7)%226);shade[i]=i*13+5;}
 for(unsigned i=0;i<128;i++)src[i]=i*29;
 for(unsigned k=0;k<40000;k++){
  for(unsigned i=0;i<1688;i++)actual[i]=expected[i]=rnd();
  _g_gamestate=k%3?GS_LEVEL:0;unsigned h=k%5*8,v=(k/5)%4*8+8,m=(k/20)%2;
  r57_view.xmin=(m?6:2)+h/4;r57_view.xend=(m?70:76)-h/4;r57_view.ymin=2+v/4;r57_view.yend=44-v/4;
  draw_column_vars_t d={(int)(rnd()%44)-3,(int)(rnd()%34)-6,(int)(rnd()%34)-6,rnd(),(int32_t)(rnd()%2000000)-1000000,src,k%2?shade:0};
  const uint16_t *map=k%3?maps:0;
  R39M_Texture((uint8_t *)(actual+8),&d,map,colors,d.colormap);
  uint16_t f=(uint16_t)((d.texturemid>>7)+(d.yl-CENTERY)*d.fracstep);
  for(int y=d.yl;y<=d.yh;y++,f=(uint16_t)(f+d.fracstep))if(vis(d.x,y)){
   uint8_t c=src[f>>9];uint16_t cell;
   if(map)cell=map[c];else{if(d.colormap)c=shade[c];cell=colors[c];}
   expected[8+y*38+d.x]=cell;
  }
  assert(!memcmp(actual,expected,sizeof actual));
  int16_t lo=d.yl,hi=d.yh;
  if(R39M_Clip(d.x,&lo,&hi)){
   uint16_t c=maps[rnd()%256];R39M_Fill((uint8_t *)(actual+8),d.x,lo,hi,c);
   for(int y=d.yl;y<=d.yh;y++)if(vis(d.x,y))expected[8+y*38+d.x]=c;
   assert(!memcmp(actual,expected,sizeof actual));
  }
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'test.c';p.write_text(code)
    subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-fsanitize=undefined',
       '-I',str(r/'scripts/lab/r39modern'),str(p),'-o',str(p.with_suffix(''))],check=True)
    subprocess.run([str(p.with_suffix(''))],check=True)
print('PASS 40,000 tile-word texture/fill cases, all four palette bits, clipping, fraction wrap, canaries')
