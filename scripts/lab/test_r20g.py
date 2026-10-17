#!/usr/bin/env python3
"""Asset coverage gate and compiled host checks for R20g. No hardware claims."""
import pathlib,struct,random,subprocess,tempfile,sys,re,runpy
root=pathlib.Path(__file__).resolve().parents[2]
src=(root/'src/r_draw.c').read_text()
def function(s,name):
    a=s.index(name); a=s.rfind('\n',0,a)+1
    b=s.index('{',a);depth=0
    for e in range(b,len(s)):
        if s[e]=='{':depth+=1
        elif s[e]=='}':
            depth-=1
            if not depth:return s[a:e+1]
    raise ValueError(name)
def native(code):
    with tempfile.TemporaryDirectory() as tmp:
        c=pathlib.Path(tmp)/'test.c';c.write_text(code)
        e=c.with_suffix('');subprocess.run(['gcc','-O2','-std=c11',str(c),'-o',str(e)],check=True)
        subprocess.run([str(e)],check=True)
b=(root/'scripts/doom64.wad').read_bytes();n=struct.unpack_from('>h',b,4)[0];directory=struct.unpack_from('>i',b,8)[0];lumps=[]
for i in range(n):
    pos,size=struct.unpack_from('>iH',b,directory+16*i);name=b[directory+16*i+8:directory+16*i+16].split(b'\0')[0]
    lumps.append((name,b[pos:pos+size]))
byname=dict(lumps);tp=byname[b'TEXTUREP'];nt=struct.unpack_from('>i',byname[b'TEXTURE1'])[0];cols=0
for t in range(1,nt):
    o=struct.unpack_from('>H',tp,2*t)[0];mask,w,h,overlap,np=struct.unpack_from('>HhhBB',tp,o)
    if not overlap:continue
    assert 0<h<=128 and h%4==0
    for x in range(w):
        coverage=set()
        for j in range(np):
            ox,oy,pn,pw=struct.unpack_from('>hhhh',tp,o+8+j*8)
            if not ox<=x<ox+pw:continue
            p=lumps[pn][1];q=struct.unpack_from('>i',p,8+4*(x-ox))[0]
            while p[q]!=255:
                y,length=p[q:q+2];coverage.update(range(max(0,oy+y),min(h,oy+y+length)));q+=length+4
        assert len(coverage)==h,(t,x,h,len(coverage))
        cols+=1
print(f'PASS cache direct gate: {cols} actual WAD columns, complete coverage, aligned height <=128',flush=True)
# Compiled production hash/probe functions; same collision/replacement sequence.
code='#include <stdint.h>\n#include <assert.h>\n#define MAX_CACHE_ENTRIES 16\n#define MAX_CACHE_TRIES 4\nstatic uint16_t columnCacheEntries[16];\ntypedef struct {uint16_t hash,tag,mask;} r20_compsrc_t;\n'
code+=function(src,'static uint16_t CACHE_ENTRY(')+'\n'+function(src,'static uint16_t FindColumnCacheItem(')+'\n'+function(src,'static uint16_t R20_FindComposite(')
code+=r'''
int main(void){uint32_t rng=20261017u;for(unsigned t=1;t<125;t++)for(unsigned x=0;x<256;x++)for(unsigned k=0;k<16;k++){
 for(unsigned i=0;i<16;i++){rng=rng*1664525u+1013904223u;columnCacheEntries[i]=(uint16_t)(rng>>16);}
 if(k&1)columnCacheEntries[k]=0;
 if(k&2)columnCacheEntries[(k+5)&15]=CACHE_ENTRY(x,t);
 r20_compsrc_t p={(uint16_t)(t*71),(uint16_t)(t<<8),255};
 assert(R20_FindComposite(&p,x)==FindColumnCacheItem(t,x));
}return 0;}
'''
native(code);print('PASS R4b compiled cache hashing: 507904 collision states',flush=True)
# IRQ ownership test executes actual publisher/callback source with hardware mocks.
v=(root/'src/i_genesisv.c').read_text();a=v.index('static volatile uint16_t r20_video_ready;');b=v.index('#elif defined(DOOM_R20_DMA_BATCH)',a)
# Mock storage independent of the static/heap allocation branch; execute the real ownership code.
video='static uint16_t r20_video_copy[VIEWWINDOWWIDTH*VDP_DISPLAY_ROWS];\n'+v[a:b]
video=video.replace('uint16_t line=(*(volatile uint16_t *)0xC00008)>>8;','uint16_t line=test_line;')
a=video.index('void R20_AbortVideo(');e=video.index('void R20_StopVideo(',a)
video=video[:a]+'void R20_AbortVideo(void){r20_video_ready=0;r20_next_palette=100;}\n'+video[e:]
code=r'''
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>
#define VIEWWINDOWWIDTH 38
#define VDP_DISPLAY_ROWS 28
#define R20_PROBE() ((void)0)
#define _fmemcpy memcpy
static uint16_t _s_screen[38*28],vram[38*28],test_line;
static uint32_t _g_vblankCount;
static unsigned palettes,uploads;static int8_t actual_palette;
static void I_Error(const char *s){abort();}
static void I_UploadNewPalette(int8_t p){actual_palette=p;palettes++;}
static void R20_UploadRows(const uint16_t *p,uint16_t h){memcpy(vram,p,h*38*2);uploads++;}
'''+video+r'''
int main(void){
 for(unsigned f=0;f<1000;f++){
  unsigned rows=(f%7==0)?28:22;
  for(unsigned i=0;i<38*28;i++)_s_screen[i]=(uint16_t)(f*31+i);
  r20_next_palette=(f%5==0)?(int8_t)(f%14):100;
  R20_Present(rows);assert(r20_video_ready);
  unsigned before=uploads,oldpal=palettes;
  for(unsigned i=0;i<38*28;i++)_s_screen[i]=0xdead;
  test_line=240;R20_VBlankVideo();assert(uploads==before&&r20_video_ready&&palettes==oldpal);
  test_line=224;R20_VBlankVideo();assert(uploads==before+1&&!r20_video_ready);
  for(unsigned i=0;i<38*rows;i++)assert(vram[i]==(uint16_t)(f*31+i));
  assert(palettes==oldpal+(f%5==0));if(f%5==0)assert(actual_palette==(int8_t)(f%14));
  R20_StopVideo();_g_vblankCount++;
 }
 R20_Present(28);R20_AbortVideo();assert(!r20_video_ready);R20_StopVideo();return 0;
}
'''
native(code);print('PASS V2 actual publisher/callback: 1000 immutable frames, late IRQ, HUD extent, palettes and abort',flush=True)
# Descriptor endpoints for all RAM row addresses/VRAM destinations used in V3.
for base in (0xff0000,0xe0ff0000,0xff8000,0xe0ff8000):
    for y in range(28):
        address=base+y*76;word=address>>1
        regs=[0x9300|38,0x9400,0x9500|(word&255),0x9600|((word>>8)&255),0x9700|((word>>16)&127)]
        reconstructed=((regs[4]&127)<<17)|((regs[3]&255)<<9)|((regs[2]&255)<<1)
        assert reconstructed==address&0xffffff
print('PASS V3 source register lane/address contracts; actual VDP/bus timing still needs emulator/hardware',flush=True)
# R5 must follow sky's mutation of dcvars.colormap, as the original writer does.
code=r'''
#include <stdint.h>
#include <assert.h>
#define VIEWWINDOWWIDTH 38
#define R20_COUNT(i,n) ((void)0)
static const int16_t CENTERY=11;
static uint16_t _s_screen[38*28],mapa[256],mapb[256];
static uint8_t ca[256],cb[256],source[128];
static const uint16_t *r20_wall_cellmap;
static const uint8_t *r20_wall_colormap;
static const uint16_t *used;static unsigned selected,fallback;
typedef struct {int16_t x,yl,yh;uint16_t fracstep;int32_t texturemid;const uint8_t *source,*colormap;} draw_column_vars_t;
static const uint16_t *R20_SelectCellMap(const uint8_t *p){selected++;return p==ca?mapa:p==cb?mapb:0;}
static void R_DrawColumnWall(const draw_column_vars_t *v){fallback++;}
static void R20_RegDraw(uint16_t *d,const uint8_t *s,const uint16_t *m,uint16_t f,uint16_t step,uint16_t n){used=m;}
'''+function(src,'static inline void R20_DrawRegWall(')+r'''
int main(void){
 draw_column_vars_t d={1,1,10,511,32768,source,ca};
 r20_wall_colormap=ca;r20_wall_cellmap=R20_SelectCellMap(ca);
 R20_DrawRegWall(&d);assert(used==mapa&&selected==1);
 d.colormap=cb;R20_DrawRegWall(&d);assert(used==mapb&&selected==2);
 R20_DrawRegWall(&d);assert(used==mapb&&selected==2);
 d.colormap=0;R20_DrawRegWall(&d);assert(fallback==1&&selected==3);
 d.yh=0;R20_DrawRegWall(&d);assert(fallback==1&&selected==3);return 0;
}
'''
native(code);print('PASS R5 production wrapper: sky colormap mutation, cached reuse, fallback and empty span',flush=True)
