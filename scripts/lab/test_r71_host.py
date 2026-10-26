#!/usr/bin/env python3
"""R71 host gate: real extracted R42 reference vs real B1b entry; OFS exhaustive 76x44 oracle.
No stubbed fast-path conditions: B1b/R42 functions are extracted from src/r22_video.inc.
R60 ASM is replaced by a byte-identical C **simulation** for native host compilation only.
Real compiled M68k/BlastEm framebuffer comparison is a second mandatory gate.
"""
from pathlib import Path
import re
import subprocess
import tempfile

root=Path(__file__).resolve().parents[2]
s=(root/'src/r22_video.inc').read_text()
def function(sig):
    p=s.index(sig)
    start=s.index('{',p)
    depth=0
    for q in range(start,len(s)):
        if s[q]=='{': depth+=1
        if s[q]=='}':
            depth-=1
            if depth==0: return s[p:q+1]
    raise RuntimeError('unbalanced '+sig)

def initializer(name,count):
    m=re.search(r'static const uint16_t '+name+r'\['+str(count)+r'\]\s*=\s*\{([^}]+)\};',s,re.S)
    assert m,name
    v=[int(x) for x in re.findall(r'\b\d+\b',m.group(1))]
    assert len(v)==count,(name,len(v))
    return v,m.group(0)

row,rd=initializer('r71_rowofs',22)
col,cd=initializer('r71_colofs',76)
for y in range(44):
    for x in range(76):
        original=(y>>1)*152+(x&1)*76+(x>>1)*2+1
        assert row[y>>1]+col[x]==original,(x,y)
        assert 0<=original<3344
assert row[21]+col[75]==3343
print('PASS OFS: 3344 exhaustive physical samples, exact original Pair-V offsets, ROM-only tables',flush=True)

reference=function('static void R42_DrawPackedWall(')
fast=function('void R71_DrawColumnWallFast(')
ofs_fn=function('static inline uint8_t *R71_PixelByte(')
assert 'R42_DrawPackedWall(v);' in fast and 'R60_WallDraw' in fast
assert 'R71_PixelByte(' in fast
assert 'R71_PixelByte(' in reference

program=r"""
#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define DOOM_R64A_PROLOGUE 1
#define DOOM_R60_PAIR_ASM 1
#define DOOM_R52_CPLUT 1
#define DOOM_R48_PAIR_V 1
#define DOOM_R48_V_FAST 1
#define DOOM_R47_PLANE_PAIR 1
#define DOOM_R56_DUAL_COLOR 1
#define DOOM_R59_COLOR_VIEW 1
#define DOOM_R57_CROP16 1
#define DOOM_R57_VIEW_MENU 1
#define DOOM_R71_B1B 1
#define R52_COLORMAP_BYTES 8192
#define CENTERY 22
#define R48_COUNT(n,v) ((void)0)
#define R48_WALL_CALLS 1
#define R48_WALL_PIXELS 2
#include "r22_pixel4.h"
typedef struct {int16_t x,yl,yh;uint16_t fracstep;int32_t texturemid;const uint8_t *source,*colormap;} draw_column_vars_t;
typedef struct {
    const uint8_t *comp[2];
    const uint8_t *flat[2];
    int16_t border,xmin,xend,yend;
} r64a_ctx_t;
static r64a_ctx_t r64a_ctx,ctx_fallback;
static struct {uint32_t before;uint8_t pixels[R22_FB_BYTES];uint32_t after;} r22_fb;
static uint8_t r22_color[256], walls_even[256], walls_odd[256];
static uint8_t cmem[8192+256],outside_cm[256],sourcebuf[128],composed[2][8192];
static const uint8_t *fullcolormap=cmem;
typedef struct {const uint8_t *wall_even,*wall_odd;} r71_mode_t;
static r71_mode_t mode={walls_even,walls_odd};
#define R59_CURRENT mode
static inline const r64a_ctx_t *R64A_Get(r64a_ctx_t *tmp) {
    if(r64a_ctx.comp[0]) return &r64a_ctx;
    *tmp=ctx_fallback; return tmp;
}
static inline const uint8_t *R64A_LUT(const r64a_ctx_t *cx,const uint8_t *colormap,uint16_t parity) {
    if(!colormap)return 0;
    uint32_t diff=(uint32_t)((uintptr_t)colormap-(uintptr_t)fullcolormap);
    if(diff>=R52_COLORMAP_BYTES || (diff&255u)!=0u)return 0;
    return cx->comp[parity]+diff;
}
static void R60_WallDraw(uint8_t *dst, const uint8_t *src,const uint8_t *lut,
  uint16_t frac,uint16_t step,uint16_t count,uint16_t odd_head) {
    uint16_t yodd=odd_head;
    for(uint16_t i=0;i<count;i++) {
        uint8_t c=lut[src[frac>>9]]&15;
        if(yodd) {
            *dst=(uint8_t)((*dst&0xf0u)|c);
            dst+=152;
        } else
            *dst=(uint8_t)((*dst&0x0fu)|(c<<4));
        frac=(uint16_t)(frac+step);
        yodd^=1u;
    }
}
static uint32_t rng=0x71b1b026u;
static uint32_t next(void){rng=rng*1664525u+1013904223u;return rng;}
"""
source_ref=reference+'\n'+fast
source_ofs=rd+'\n'+cd+'\n'+ofs_fn+'\n'
tail=r"""
int main(void) {
    unsigned taken=0, possible=0;
    for(unsigned i=0;i<256;i++) {
        walls_even[i]=(uint8_t)(next()&15);
        walls_odd[i]=(uint8_t)(next()&15);
        r22_color[i]=(uint8_t)(next()&15);
        outside_cm[i]=(uint8_t)next();
    }
    for(unsigned i=0;i<128;i++)sourcebuf[i]=(uint8_t)next();
    for(unsigned i=0;i<8192;i++) {
        cmem[i]=(uint8_t)next();
        composed[0][i]=walls_even[cmem[i]];
        composed[1][i]=walls_odd[cmem[i]];
    }
    for(unsigned i=0;i<256;i++)cmem[8192+i]=(uint8_t)next();
    ctx_fallback=(r64a_ctx_t){{composed[0],composed[1]},{0,0},2,2,76,44};
    for(unsigned t=0;t<40000;t++) {
        unsigned state=next();
        int16_t x=(int16_t)((int)(next()%88)-6);
        int16_t y0=(int16_t)((int)(next()%63)-12);
        int16_t y1=(int16_t)(y0+(int)(next()%69)-10);
        if(t%19==0){x=75;y0=43;y1=43;}
        if(t%23==0){x=0;y0=0;y1=43;}
        if(t%29==0){x=20;y0=21;y1=22;}
        if(t%31==0){x=37;y0=22;y1=43;}
        const uint8_t *colormap;
        switch(t%6) {
        case 0: colormap=NULL;break;
        case 1: colormap=cmem+(next()%32)*256;break;
        case 2: colormap=cmem+1;break;
        case 3: colormap=outside_cm;break;
        case 4: colormap=cmem+8192;break;
        default: colormap=cmem;break;
        }
        int16_t xmins[]={0,2,4,8,16},borders[]={0,2,4,8,12};
        int16_t xends[]={76,74,72,68,60},yends[]={44,42,40,36,32};
        unsigned modeidx=state%5;
        r64a_ctx=(r64a_ctx_t){{composed[0],composed[1]},{0,0},
           borders[modeidx],xmins[modeidx],xends[modeidx],yends[modeidx]};
        if(t%13==0)r64a_ctx.comp[0]=NULL; /* frame context invalid: fallback */
        draw_column_vars_t v={x,y0,y1,(uint16_t)next(),(int32_t)next(),sourcebuf,colormap};
        uint8_t prev[R22_FB_BYTES],expected[R22_FB_BYTES];
        for(unsigned i=0;i<R22_FB_BYTES;i++)prev[i]=(uint8_t)next();
        memcpy(r22_fb.pixels,prev,sizeof(prev));
        r22_fb.before=r22_fb.after=0xa55a7e71;
        R42_DrawPackedWall(&v);
        memcpy(expected,r22_fb.pixels,sizeof(expected));
        memcpy(r22_fb.pixels,prev,sizeof(prev));
        R71_DrawColumnWallFast(&v);
        if(memcmp(r22_fb.pixels,expected,sizeof(expected))) {
            for(unsigned j=0;j<R22_FB_BYTES;j++)if(r22_fb.pixels[j]!=expected[j]){
                fprintf(stderr,"DIFF t=%u x=%d yl=%d yh=%d cm=%u ctx=%u firstbyte=%u expected=%u got=%u\n",
                    t,x,y0,y1,t%6,modeidx,j,expected[j],r22_fb.pixels[j]);return 2;
            }
        }
        assert(r22_fb.before==0xa55a7e71&&r22_fb.after==0xa55a7e71);
        possible+=(t%6==1 && y1>=y0 && y1-y0+1>=2 && y0>=0 && y1<44 && x>=0 && x<76);
        taken++;
    }
    assert(possible>20);
    printf("PASS B1b: %u reference vs actual extracted fast-path calls; context invalid, crop/H32-like bounds, sky-style fullcolormap, parity, COLPAIR source, clipping; candidate inputs=%u\\n",taken,possible);
}
"""
for label, extra in [('b1b-only','#define R71_PixelByte R22_PixelByte\n'),('b1b-ofs','')]:
    code=program+extra+('#define DOOM_R71_OFS 1\n' if not extra else '')+(source_ofs if not extra else '')+source_ref+tail
    with tempfile.TemporaryDirectory(prefix='r71-'+label+'-') as td:
        f=Path(td)/'test.c'
        f.write_text(code)
        out=Path(td)/'test'
        cmd=['cc','-std=gnu11','-O2','-Wall','-Wno-unused-variable','-fsanitize=undefined,address',
             '-fno-sanitize-recover=all','-iquote'+str(root/'src'),str(f),'-o',str(out)]
        subprocess.run(cmd,check=True)
        subprocess.run([str(out)],check=True)
print('PASS R71 native equivalence',flush=True)
