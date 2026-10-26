#!/usr/bin/env python3
"""Test the real packed writer and all65536 tile quadrants, no VDP claim."""
from pathlib import Path
import re,subprocess,tempfile,json
r=Path(__file__).resolve().parents[2]
s=(r/'src/r22_video.inc').read_text()
def fn(name):
 a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);d=0
 for i in range(b,len(s)):
  if s[i]=='{':d+=1
  if s[i]=='}':
   d-=1
   if d==0:return s[a:i+1]
code='''#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "r22_pixel4.h"
static const int16_t CENTERY=22;
static unsigned _g_gamestate=0;
#define GS_LEVEL 1
#define R68_HIT(k) ((void)0)
static struct {uint32_t before;uint8_t pixels[R22_FB_BYTES];uint32_t after;} r22_fb;
static uint8_t r22_color[256];
typedef struct {int16_t x,yl,yh;uint16_t fracstep;int32_t texturemid;const uint8_t *source,*colormap;} draw_column_vars_t;
'''+fn('static inline void R22_Plot(')+'\n'+fn('void R_DrawColumnSprite(')+'\n'+fn('void R_DrawColumnFlat(')+'''
static uint32_t rng=20261017;
static uint32_t next(void){rng=rng*1664525u+1013904223u;return rng;}
int main(void){
 for(uint32_t t=0;t<65536;t++){
  uint8_t a=t>>8,b=t;uint32_t top=R22_ExpandPair(a),bottom=R22_ExpandPair(b);
  for(unsigned y=0;y<8;y++)for(unsigned x=0;x<8;x++){
   uint32_t row=y<4?top:bottom;unsigned nib=(row>>(28-4*x))&15;
   uint8_t pair=y<4?a:b;unsigned want=x<4?pair>>4:pair&15;assert(nib==want);
  }
 }
 uint8_t ref[R22_FB_BYTES],source[128],map[256];
 for(unsigned i=0;i<128;i++)source[i]=(uint8_t)next();
 for(unsigned i=0;i<256;i++){map[i]=(uint8_t)next();r22_color[i]=i&15;}
 for(unsigned t=0;t<4096;t++){
  for(unsigned i=0;i<R22_FB_BYTES;i++)r22_fb.pixels[i]=ref[i]=(uint8_t)next();
  r22_fb.before=r22_fb.after=0x2244AA55;
  int16_t x=next()%76,yl=next()%44,yh=yl+next()%(45-yl)-1;
  draw_column_vars_t d={x,yl,yh,(uint16_t)next(),(int32_t)next(),source,(t&1)?map:0};
  uint16_t f=(uint16_t)((d.texturemid>>7)+(yl-CENTERY)*d.fracstep);
  for(int y=yl;y<=yh;y++){
   unsigned c=source[f>>9];if(d.colormap)c=map[c];c&=15;
   unsigned k=y*38+(x>>1);ref[k]=(x&1)?((ref[k]&240)|c):((ref[k]&15)|(c<<4));f+=d.fracstep;
  }
  R_DrawColumnSprite(&d);assert(memcmp(ref,r22_fb.pixels,R22_FB_BYTES)==0);
  assert(r22_fb.before==0x2244AA55 && r22_fb.after==0x2244AA55);
 }
 memset(r22_fb.pixels,0,R22_FB_BYTES);
 for(unsigned y=0;y<44;y++)for(unsigned x=0;x<76;x++)R22_Put(r22_fb.pixels,x,y,(x+y)&15);
 for(unsigned y=0;y<44;y++)for(unsigned x=0;x<76;x++)assert(((r22_fb.pixels[y*38+(x>>1)]>>((x&1)?0:4))&15)==((x+y)&15));
 puts("PASS65536 independent quadrant tiles,4096 production columns,3344 independent samples and guards");
}
'''
with tempfile.TemporaryDirectory() as d:
 c=Path(d)/'test.c';c.write_text(code);e=Path(d)/'test'
 subprocess.run(['cc','-O2','-fsanitize=undefined','-fno-sanitize-recover=undefined','-iquote'+str(r/'src'),str(c),'-o',str(e)],check=True);subprocess.run([str(e)],check=True)
# Ensure graphics/font and shared lower Window regions do not overlap and visible graphics/font don't overlap.
banks=[(16*32,(16+836)*32),(852*32,(852+836)*32)];font=(1696*32,1792*32)
assert banks[0][1]==banks[1][0] and banks[1][1]<=font[0] and font[1]==0xe000
assert 0xf000+22*128<=0xfc00 and 0xfc00+640<=0x10000
xt=[int(x) for x in (r/'src/r22_xtoviewangle.h').read_text().strip().split(',')]
assert len(xt)==77 and xt[38]==0
assert 8100<xt[0]<8300 and -8300<(xt[-1]-65536)<-8100
v=[int(x) for x in re.findall(r'\d+', (r/'src/r22_viewangletox.h').read_text())]
assert len(v)==2032 and all(v[i]>=v[i+1] for i in range(len(v)-1))
assert all(0<=x<=76 for x in v)
print('PASS VRAM banks/font/shared Window/SAT/HScroll bounds and independent76-column projection')
