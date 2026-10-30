#!/usr/bin/env python3
from pathlib import Path
import argparse,subprocess,tempfile,re
ap=argparse.ArgumentParser();ap.add_argument('--generated',action='store_true');a=ap.parse_args()
r=Path(__file__).resolve().parents[2]
s=(r/'src/r92_shadow.inc').read_text();start=s.index('static void R92_ShadowPass')
code='''#include <stdint.h>
#include <assert.h>
#include <string.h>
typedef struct{uint8_t y0,y1,x0,x1;}r92_rect_t;
static r92_rect_t r92_rect;
'''+s[start:]+'''
int main(void){static uint32_t table[65536];static uint16_t maps[2][2][256],cost[2][2][256];uint16_t out[1672],before[1672];for(unsigned k=0;k<65536;k++)table[k]=((0x8100u|(k>>8))<<16)|(0x2200u|(k&255));
for(unsigned p=0;p<2;p++)for(unsigned crop=0;crop<5;crop++){r92_rect=(r92_rect_t){(uint8_t)(1+crop),(uint8_t)(22-crop),(uint8_t)(crop*2),(uint8_t)(38-crop*2)};for(unsigned k=0;k<1672;k++)out[k]=before[k]=(uint16_t)(k*71);R92_ShadowPass(out,table,maps,cost,p);
for(unsigned y=0;y<22;y++)for(unsigned x=0;x<38;x++){unsigned aa=y*76+x,bb=aa+38;int in=y>=r92_rect.y0&&y<r92_rect.y1&&x>=r92_rect.x0&&x<r92_rect.x1;if(!in){assert(out[aa]==before[aa]&&out[bb]==before[bb]);}else if(!p){uint32_t v=table[((before[aa]&255)<<8)|(before[bb]&255)];assert(out[aa]==v>>16&&out[bb]==(uint16_t)v);}else assert(!out[aa]&&!out[bb]);}}return 0;}
'''
with tempfile.TemporaryDirectory() as td:
 c=Path(td)/'t.c';c.write_text(code);subprocess.run(['cc','-O2',str(c),'-o',str(c.with_suffix(''))],check=True);subprocess.run([str(c.with_suffix(''))],check=True)
if a.generated:
 inc=(r/'src/r77_menu.inc').read_text();assert 'VDP_setHilightShadow(TRUE)' not in inc
 h=(r/'src/hud_wad_assets.h').read_text()
 def array(name):
  m=re.search(r'\b'+name+r'((?:\[\d+\])+)\s*=\s*\{(.*?)\};',h,re.S);assert m,name
  dims=list(map(int,re.findall(r'\d+',m[1])));return dims,[int(v,0) for v in re.findall(r'0x[\da-fA-F]+|\d+',m[2])]
 dims,bg=array('hudw_bgmap');_,tiles=array('hudw_tiles');_,pal=array('hudw_pal')
 health=int(re.search(r'#define HUDW_HEALTH_C\s+(\d+)',h)[1]) if '#define HUDW_HEALTH_C' in h else 5
 for phase in (0,1):
  tile=bg[dims[1]+health+1+phase]
  for row in tiles[tile*8:tile*8+8]:
   assert pal[15]==0xEEE or all((row>>shift)&15!=15 for shift in range(0,32,4)),'Stone uses reserved white slot'
print('PASS actual C rect pass, fallback, untouched excluded tiles; menu checks when generated')
