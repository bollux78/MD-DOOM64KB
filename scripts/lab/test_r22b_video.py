#!/usr/bin/env python3
"""Production uploader/text with a mocked VDP; this is not VDP emulation."""
from pathlib import Path
import subprocess,tempfile,re
r=Path(__file__).resolve().parents[2];s=(r/'src/r22_video.inc').read_text()
def fn(name):
 a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);d=0
 for i in range(b,len(s)):
  if s[i]=='{':d+=1
  if s[i]=='}':
   d-=1
   if not d:return s[a:i+1]
u=fn('static void R22_UploadBack(')
u=re.sub(r'    volatile uint32_t \*data=.*?;\n','',u)
u=u.replace('*ctrl=VDP_WRITE_VRAM_ADDR(tile*32u);','address(tile*32u);')
u=re.sub(r'\*data=(top|bottom);',r'write32(\1);',u)
t=fn('static void R22_DrawText(')
t=re.sub(r'    volatile uint32_t \*ctrl=.*?;\n','',t);t=re.sub(r'    volatile uint16_t \*data=.*?;\n','',t)
t=t.replace('*ctrl=VDP_WRITE_VRAM_ADDR(plane+y*128+x*2);','address(plane+y*128+x*2);')
t=t.replace('*data=0x8000u+(uint16_t)TILE_FONT_INDEX+c-32;','write16(0x8000u+(uint16_t)TILE_FONT_INDEX+c-32);')
code=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "r22_pixel4.h"
#include "r22_pair_lut.h"
#define TRUE 1
#define VDP_BG_A 0xE000
#define VDP_BG_B 0xF000
#define TILE_FONT_INDEX 1696
static struct {uint8_t pixels[R22_FB_BYTES];} r22_fb;
static uint16_t r22_map[38*21];
static uint8_t r22_overlay_dirty;
static uint32_t addr,writes;
static unsigned locked,pending,stops;
static uint8_t vram[65536];
static void R20_StopVideo(void){assert(!locked);pending=0;stops++;}
static uint16_t R22_Lock(void){assert(!locked && !pending);locked=1;return 0x2300;}
static void R22_Unlock(uint16_t sr){assert(locked && sr==0x2300);locked=0;}
static void VDP_setAutoInc(unsigned n){assert(locked && n==2);}
static void address(unsigned a){assert(locked && a<65536);addr=a;}
static void write16(uint16_t x){assert(locked && addr+2<=65536);vram[addr++]=x>>8;vram[addr++]=x;writes+=2;}
static void write32(uint32_t x){write16(x>>16);write16(x);}
static void VDP_clearTileMap(unsigned plane,unsigned ind,unsigned n,unsigned wait){
 assert(locked && !pending && plane==VDP_BG_B && !ind && n==64*22 && wait);
 memset(vram+plane,0,n*2);
}
'''+fn('static inline uint32_t R22_Expand(')+'\n'+u+'\n'+t+'\n'+fn('static void R22_ClearOverlay(')+'\n'+fn('void R22_BeginFrame(')+r'''
static uint16_t word(unsigned a){return (vram[a]<<8)|vram[a+1];}
int main(void){
 for(unsigned p=0;p<256;p++)assert(r22_pair_lut[p]==R22_ExpandPair(p));
 for(unsigned t=0;t<65536;t++){
  unsigned a=t>>8,b=t&255;
  assert(R22_TileIndex(a,b,1234)==((a==b && a/16==a%16)?a%16:1234));
 }
 /* All quadrant combinations traverse the actual uploader in both banks.
    Preload16 immutable solid tiles; never change them during a frame. */
 memset(vram,0xa5,sizeof(vram));
 for(unsigned c=0;c<16;c++)memset(vram+c*32,c*17,32);
 for(unsigned frame=0;frame<84;frame++){
  unsigned bank=frame&1,expected_writes=0;
  for(unsigned i=0;i<798;i++){
   unsigned t=(frame*798+i)&65535;unsigned y=i/38+1,x=i%38;
   r22_fb.pixels[2*y*38+x]=t>>8;r22_fb.pixels[(2*y+1)*38+x]=t;
  }
  writes=0;R22_UploadBack(bank);assert(!locked);
  for(unsigned i=0;i<798;i++){
   unsigned y=i/38+1,x=i%38;unsigned a=r22_fb.pixels[2*y*38+x],b=r22_fb.pixels[(2*y+1)*38+x];
   unsigned tile=16+bank*836+38+i;
#ifdef DOOM_R22_SOLID_TILES
   tile=r22_map[i];if(tile>=16)expected_writes+=32;
#else
   expected_writes+=32;
#endif
   for(unsigned yy=0;yy<8;yy++)for(unsigned xx=0;xx<8;xx++){
    unsigned packed=vram[tile*32+yy*4+xx/2];unsigned got=(xx&1)?packed&15:packed>>4;
    unsigned pair=yy<4?a:b,want=xx<4?pair>>4:pair&15;assert(got==want);
   }
  }
  assert(writes==expected_writes);
  for(unsigned c=0;c<16;c++)for(unsigned i=0;i<32;i++)assert(vram[c*32+i]==c*17);
  for(unsigned i=0xD400;i<65536;i++)assert(vram[i]==0xa5);
 }
 memset(r22_fb.pixels,0x55,sizeof(r22_fb.pixels));writes=0;R22_UploadBack(0);
#ifdef DOOM_R22_SOLID_TILES
 assert(!writes); /* Entirely uniform frame sends zero pattern bytes. */
#else
 assert(writes==798*32);
#endif
 /* Title-only and menu frames both wait BEFORE touching the VDP. */
 pending=1;r22_overlay_dirty=0;stops=0;R22_BeginFrame();assert(!pending && stops==1);
 pending=1;r22_overlay_dirty=1;R22_BeginFrame();assert(!pending && !r22_overlay_dirty);
 for(unsigned i=0xFC00;i<65536;i++)assert(vram[i]==0xa5);
 const char text[]={'A',1,(char)255,'Z',0};pending=1;
 R22_DrawText(VDP_BG_B,text,2,3);unsigned pos=VDP_BG_B+3*128+4;
 assert(!pending && !locked && word(pos)==(0x8000+1696+'A'-32));
 assert(word(pos+2)==0x8000+1696 && word(pos+4)==0x8000+1696);
 assert(word(pos+6)==0x8000+1696+'Z'-32);
 writes=0;R22_DrawText(VDP_BG_B,"ABCDEFG",37,21);assert(writes==2);
 R22_DrawText(VDP_BG_B,"BAD",38,0);R22_DrawText(VDP_BG_B,"BAD",0,28);assert(writes==2);
 puts("PASS production uploader: all quadrants/both banks, solid reuse, LUT, title/menu VDP ownership and glyph bounds");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'t.c';p.write_text(code)
 for flags in [[],['-DDOOM_R22_SOLID_TILES'],['-DDOOM_R22_SOLID_TILES','-DDOOM_R22_PAIR_LUT']]:
  e=Path(d)/'t';subprocess.run(['cc','-O2','-fsanitize=undefined','-fno-sanitize-recover=undefined','-iquote'+str(r/'src'),*flags,str(p),'-o',str(e)],check=True);subprocess.run([str(e)],check=True)
