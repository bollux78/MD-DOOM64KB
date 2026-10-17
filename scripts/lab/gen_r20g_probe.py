#!/usr/bin/env python3
"""Freestanding MC68000 probe: production P2/P3, private register ABI and seg flat."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'dist/r20g/evidence';out.mkdir(parents=True,exist_ok=True)
v=(root/'src/i_genesisv.c').read_text();r=(root/'src/r_draw.c').read_text()
def function(s,name):
 a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);depth=0
 for e in range(b,len(s)):
  if s[e]=='{':depth+=1
  elif s[e]=='}':
   depth-=1
   if not depth:return s[a:e+1]
 raise ValueError(name)
code=r'''
#include <stdint.h>
#include <stddef.h>
#define VIEWWINDOWWIDTH 38
#define VIEWWINDOWHEIGHT 22
#define R20_COLFN
#define R20_COUNT(i,n) ((void)0)
#define DOOM_CELL_LUT 1
#define DOOM_R20_CELLMAP_MEMO 1
#define DOOM_R20_PIXEL_ADDX 1
#define DOOM_R17_PIXEL_DBRA 1
#define COLEXTRABITS 7
#define COLBITS 9
static const int16_t CENTERY=11;
uint16_t _s_screen[38*28];
static uint16_t reference[38*28],colorcell[256];
static uint8_t maps[32*256],source[128];
static const uint8_t *fullcolormap=maps;
static const uint16_t doom_colormap_cells[32][256]={
'''
for j in range(32):code+='{'+','.join(str((j*1553+i*131)&65535) for i in range(256))+'},\n'
code+='};\n#define R20_DEST(x,y) (&_s_screen[(y)*38+(x)])\n'
code+='typedef struct {int16_t x,yl,yh;uint16_t fracstep;int32_t texturemid;const uint8_t *source,*colormap;} draw_column_vars_t;\n'
writer=v[v.index('R20_COLFN void R_DrawColumnSprite('):v.index('\n\nvoid R_DrawColumnWall(')]
code+=writer.replace('R_DrawColumnSprite','R20_RefColumn')+'\n#define DOOM_R20_PIXEL_UNROLL 1\n'
code+=writer.replace('R_DrawColumnSprite','R20_P3Column')+'\n'
code+='#include "r20_reg_columns.h"\n'+function(r,'static inline __attribute__((always_inline)) void R20_SegFlat(')+'\n'
import random
rand=random.Random(20261017)
pairs=[(rand.randrange(-32768,32768),rand.randrange(-2147483648,2147483648)) for _ in range(1024)]
pairs += [(a,b) for a in (-32768,-1,0,1,32767) for b in (-2147483648,-65536,-1,0,65535,2147483647)]
code+='#define DOOM_R20_HYGIENE 1\n'+function(r,'static uint32_t mulu(')+'\n'+function(r,'static inline int16_t R15_Mul16x32Shift16U(')+'\n'
code+='static const struct {int16_t a;int32_t b;int16_t want;} m2[]={'+','.join('{%d,%d,%d}'%(a,b,(((a*b)&0xffffffff)>>16)-65536 if ((a*b)&0x80000000) else (((a*b)&0xffffffff)>>16)) for a,b in pairs)+'};\n'

code+=r'''
static uint32_t rng=20261017u;
static uint32_t next(void){rng=rng*1664525u+1013904223u;return rng;}
int main(void){
 unsigned errors=0;
 *(volatile uint16_t*)0xA00000=0;
 for(unsigned i=0;i<128;i++)source[i]=(uint8_t)(i*131);
 for(unsigned i=0;i<256;i++)colorcell[i]=(uint16_t)(i*13);
 for(unsigned test=0;test<768;test++){
  unsigned yl=next()%28,n=next()%(29-yl),x=next()%38,shade=next()%32;
  draw_column_vars_t d={(int16_t)x,(int16_t)yl,(int16_t)(yl+n-1),(uint16_t)next(),(int32_t)next(),source,maps+256*shade};
  if(test<29){d.yl=0;d.yh=(int16_t)test-1;n=test;}
  for(unsigned i=0;i<38*28;i++)_s_screen[i]=0xdead;
  R20_RefColumn(&d);
  for(unsigned i=0;i<38*28;i++){reference[i]=_s_screen[i];_s_screen[i]=0xdead;}
  R20_P3Column(&d);
  for(unsigned i=0;i<38*28;i++)if(reference[i]!=_s_screen[i]){errors++;break;}
  for(unsigned i=0;i<38*28;i++)_s_screen[i]=0xdead;
  if(n){uint16_t frac=(d.texturemid>>7)+(d.yl-CENTERY)*d.fracstep;
    R20_RegDraw(&_s_screen[d.yl*38+d.x],source,doom_colormap_cells[shade],frac,d.fracstep,n);}
  for(unsigned i=0;i<38*28;i++)if(reference[i]!=_s_screen[i]){errors++;break;}
  for(unsigned i=0;i<38*28;i++)_s_screen[i]=0xdead;
  R20_SegFlat(0x2379,d.x,d.yl,d.yh);
  for(unsigned y=0;y<28;y++)for(unsigned xx=0;xx<38;xx++){
   uint16_t want=(xx==x&&y>=(unsigned)d.yl&&y<(unsigned)(d.yl+n))?0x2379:0xdead;
   if(_s_screen[y*38+xx]!=want){errors++;goto endflat;}
  }
endflat: ;
 }
 for(unsigned i=0;i<sizeof(m2)/sizeof(*m2);i++)if(R15_Mul16x32Shift16U(m2[i].a,m2[i].b)!=m2[i].want)errors++;
 *(volatile uint16_t*)0xA00002=(uint16_t)errors;
 *(volatile uint16_t*)0xA00004=0;
 for(;;){}
}
'''
(out/'render-probe.c').write_text(code)
(out/'probe-boot.s').write_text('.section .text.boot,"ax"\n.long 0x00fffe00,entry\n.org 0x400\n.globl entry\nentry: jsr main\n bra entry\n')
(out/'probe.ld').write_text('ENTRY(entry)\nSECTIONS { . = 0; .text : { KEEP(*(.text.boot)) *(.text*) *(.rodata*) } . = 0xff0000; .bss : { *(.bss*) *(COMMON) } /DISCARD/ : { *(.comment*) *(.eh_frame*) } }\n')
print('Generated actual P2/P3/R5/R6 probe: 768 spans with full framebuffer guards')
