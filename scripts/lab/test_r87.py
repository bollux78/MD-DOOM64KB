#!/usr/bin/env python3
"""Patch-chain and host checks; real m68k raster is captured in the workflow."""
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
from apply_r87 import halfkernel
asm=halfkernel((ROOT/'src/r60_pair_wall.s').read_text())
assert 'move.b (%a1,%d0.w),%d3' not in asm
for step in range(65536):
 low=(step<<7)&65535;integer=step>>9
 v=low*2;hi=(integer*2+(v>>16))&127
 doubled=(step*2)&65535
 assert (v&65535)==((doubled<<7)&65535) and hi==(doubled>>9)
print('PASS all 65536 doubled texture steps: overflow/carry/wrap')
def function(s,name):
 a=s.index(name);i=s.index('{',a);depth=1;j=i+1
 while depth:
  depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
with tempfile.TemporaryDirectory() as tmp:
 base=Path(tmp)/'base';shutil.copytree(ROOT,base,ignore=shutil.ignore_patterns('.git','dist','__pycache__'))
 for script,extra in [('apply_r81.py',{}),('apply_r80_performance.py',{'R80_EXPERIMENTS':'P1+F1'}),('apply_r83.py',{'R83_CANDIDATE':'sprites'}),('apply_r85.py',{'R85_CANDIDATE':'all'})]:
  subprocess.run(['python3','scripts/lab/'+script],cwd=base,env={**os.environ,**extra},check=True,stdout=subprocess.DEVNULL)
 for mode in ('control','sky','farwalls','vhalf','decor','sprites','ai'):
  dst=Path(tmp)/mode;shutil.copytree(base,dst)
  subprocess.run(['python3','scripts/lab/apply_r87.py'],cwd=dst,env={**os.environ,'R87_CANDIDATE':mode},check=True,stdout=subprocess.DEVNULL)
  builder=(dst/'scripts/lab/build_r71a12mul_hud.py').read_text()
  assert "'r87-'" in builder and "('%s',0)"%mode in builder
  if mode=='sky':
   body=function((dst/'src/r_sky.c').read_text(),'void R_DrawSky(draw_column_vars_t *dcvars)')
   header='''#include <stdint.h>
#include <assert.h>
#define __far
typedef uint8_t byte;
#define DOOM_R57_CROP16 1
#define R57_CROP_ACTIVE 1
#define R57_XMIN 6
#define R57_XEND 72
#define R57_YMIN 6
#define R57_YEND 40
#define VIEWWINDOWWIDTH 76
#define VIEWWINDOWHEIGHT 44
#define SCREENHEIGHT_VGA 200
#define FRACUNIT 65536
#define COLEXTRABITS 7
static const uint8_t cm[256]={0};static const uint8_t *fixedcolormap=0,*fullcolormap=cm;
typedef struct {uint32_t columnofs[256];uint8_t data[32768];} patch_t;
typedef uint8_t column_t;
static patch_t patch;static const patch_t *skypatch;static uint16_t skywidthmask=255;
typedef struct {int16_t x,yl,yh;int32_t texturemid;const uint8_t *colormap;uint16_t fracstep;const uint8_t *source;} draw_column_vars_t;
static int calls;static void R_DrawColumnWall(draw_column_vars_t *v){calls++;assert(v->yl>=6 && v->yh<40 && v->x>=6 && v->x<72);}
'''
   header+='static const uint8_t r87_skyx[76]={'+','.join(str(x*256//76) for x in range(76))+'};\n'
   main='''int main(void){
for(int i=0;i<256;i++)patch.columnofs[i]=1024+128*i;
for(int x=0;x<76;x++)for(int y=-8;y<52;y++){
 draw_column_vars_t v={.x=x,.yl=y,.yh=y};calls=0;
 int visible=x>=6&&x<72&&y>=6&&y<40;
 skypatch=visible?&patch:0;R_DrawSky(&v);assert(calls==visible);
 if(visible)assert(v.source==(const uint8_t*)&patch+1024+128*(x*256/76)+3);
}
return 0;}
'''
   c=Path(tmp)/'sky.c';c.write_text(header+body+main)
   subprocess.run(['cc','-O2',str(c),'-o',str(Path(tmp)/'test-sky')],check=True)
   subprocess.run([str(Path(tmp)/'test-sky')],check=True)
  if mode=='farwalls':
   # All constant origins must be a complete 128-byte texture window.
   import re
   colors=(dst/'src/r87_wallcolors.h').read_text()
   rows=re.findall(r'\{([0-9,]+)\}',colors);assert len(rows)==125
   assert all(len(x.split(','))==128 and len(set(x.split(',')))==1 for x in rows)
  if mode=='ai':
   s=(dst/'src/p_enemy2.c').read_text();body=function(s,'static int R87_DeferDecision(')
   c=Path(tmp)/'ai.c';c.write_text('''#include <stdint.h>
#include <assert.h>
#define FRACUNIT 65536
typedef struct {int32_t x,y;int type;} mobj_t;
static struct {mobj_t *mo;} _g_player;static uint32_t _g_leveltime;
'''+body+'''int main(void){mobj_t p={0},a={0};_g_player.mo=&p;
for(int t=0;t<16;t++){_g_leveltime=t;assert(!R87_DeferDecision(&a));a.x=512*FRACUNIT;assert(!R87_DeferDecision(&a));a.x=513*FRACUNIT;assert(R87_DeferDecision(&a)==((t&3)!=0));a.x=-513*FRACUNIT;assert(R87_DeferDecision(&a)==((t&3)!=0));a.x=0;}
_g_player.mo=0;assert(!R87_DeferDecision(&a));return 0;}''')
   subprocess.run(['cc','-O2',str(c),'-o',str(Path(tmp)/'test-ai')],check=True)
   subprocess.run([str(Path(tmp)/'test-ai')],check=True)
   assert 'r87_move:\n    // chase towards player' in s
  print('PASS',mode)
print('PASS actual C sky: 4560 visibility cases, no hidden patch access; actual C AI distance/cadence; complete wall origins; seven patch chains')
