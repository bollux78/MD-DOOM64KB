#!/usr/bin/env python3
"""R42 Q2: native C reference vs hoisted wall-only 4bpp store.
The M68k asm variant is cross-compiled in CI and validated visually on
BlastEm/hardware; this native C oracle validates the geometry/nibble path.
"""
from pathlib import Path
import subprocess
import tempfile
r=Path(__file__).resolve().parents[2]
s=(r/'src/r22_video.inc').read_text()
def fn(name):
    p=s.index(name)
    p=s.rfind('\n',0,p)+1
    op=s.index('{',p)
    depth=0
    for q in range(op,len(s)):
        if s[q]=='{':depth+=1
        if s[q]=='}':
            depth-=1
            if depth==0:return s[p:q+1]
    raise ValueError(name)
plot=fn('static inline void R22_Plot(')
sprite=fn('void R_DrawColumnSprite(')
new=s[s.index('#if defined(DOOM_R42_WALL_HOIST) || defined(DOOM_R42_WALL_ASM)'):
      s.index('void R_DrawFuzzColumn(')]
program=r"""
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "r22_pixel4.h"
#define GS_LEVEL 1
static const int16_t CENTERY=22;
static unsigned _g_gamestate;
static struct {uint32_t before;uint8_t pixels[R22_FB_BYTES];uint32_t after;} r22_fb;
static uint8_t r22_color[256];
typedef struct {int16_t x,yl,yh;uint16_t fracstep;int32_t texturemid;const uint8_t *source,*colormap;} draw_column_vars_t;
""" + plot+"\n"+sprite+"\n"+new+r"""
static uint32_t rng=20261020;
static uint32_t next(void){rng=rng*1664525u+1013904223u;return rng;}
static void expected(const draw_column_vars_t *v,uint8_t *buf){
    int16_t n=(int16_t)(v->yh-v->yl+1);
    if(n<=0)return;
    uint16_t f=(uint16_t)((v->texturemid>>7)+(v->yl-CENTERY)*v->fracstep);
    for(int32_t y=v->yl;y<=v->yh;y++){
        uint8_t c=v->source[f>>9];
        if(v->colormap)c=v->colormap[c];
        c=r22_color[c]&15;
        int x=v->x;
        if(x>=0&&x<76&&y>=0&&y<44&&
           !(_g_gamestate==GS_LEVEL&&(x<2||y<2))){
            unsigned i=(unsigned)y*38+((unsigned)x>>1);
            buf[i]=(x&1)?(uint8_t)((buf[i]&0xf0)|c):
                           (uint8_t)((buf[i]&0x0f)|(c<<4));
        }
        f=(uint16_t)(f+v->fracstep);
    }
}
int main(void){
    uint8_t src[128],cm[256],ref[R22_FB_BYTES];
    for(unsigned i=0;i<128;i++)src[i]=(uint8_t)next();
    for(unsigned i=0;i<256;i++){cm[i]=(uint8_t)next();r22_color[i]=next()&15;}
    for(unsigned t=0;t<20000;t++){
        for(unsigned i=0;i<R22_FB_BYTES;i++)r22_fb.pixels[i]=ref[i]=(uint8_t)next();
        r22_fb.before=r22_fb.after=0x2244aa55;
        int16_t x=(int16_t)((int)(next()%85)-4);
        int16_t yl=(int16_t)((int)(next()%53)-6);
        int16_t yh=(int16_t)(yl+(next()%54));
        draw_column_vars_t v={x,yl,yh,(uint16_t)next(),(int32_t)next(),src,(t&1)?cm:0};
        _g_gamestate=(t&2)?GS_LEVEL:0;
        expected(&v,ref);
        R_DrawColumnWall(&v);
        assert(!memcmp(r22_fb.pixels,ref,R22_FB_BYTES));
        assert(r22_fb.before==0x2244aa55&&r22_fb.after==0x2244aa55);
    }
    puts("R42 Q2 PASS: 20000 original-vs-hoisted pixel4 wall columns, edges, overlapping neighbor nibbles, guards");
}
"""
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'q2.c';p.write_text(program)
    exe=Path(d)/'q2'
    subprocess.run(['cc','-std=gnu11','-O2','-DDOOM_R42_WALL_HOIST',
         '-fsanitize=undefined,address','-fno-sanitize-recover=all',
         '-iquote'+str(r/'src'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
