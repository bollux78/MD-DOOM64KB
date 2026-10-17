#!/usr/bin/env python3
"""Compare both compiled versions of the actual scale function and clamps.
Uses the actual sine table and original fixed helpers, in a native host build.
"""
import pathlib,re,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[2]
src=(root/'src/r_draw.c').read_text();tables=(root/'src/tables.c').read_text()
def extract(text,name):
 m=re.search(r'[^\n;{}]*\b'+name+r'\([^\n]*\)\n\{',text);assert m,name
 start=m.start();depth=0
 for i in range(m.end()-1,len(text)):
  if text[i]=='{':depth+=1
  elif text[i]=='}':
   depth-=1
   if not depth:return text[start:i+1]
 raise AssertionError(name)
table=re.search(r'static const uint16_t finesineTable_part_1\[2048\]\s*=\s*\{.*?\};',tables,re.S).group()
code='''#include <stdint.h>
#include <stdlib.h>
#include "r20_scale_math.h"
typedef int32_t fixed_t;
typedef int boolean;
#define CONSTFUNC
#define D_abs labs
#define FRACUNIT 65536
#define FRACBITS 16
#define VIEWWINDOWHEIGHT 22
#define FINEANGLES 8192
#define ANG90_16 16384
#define ANGLETOFINESHIFT_16 3
#define FixedReciprocalSmall(v) (0xffffffffu/(uint16_t)(v))
#define FixedReciprocalBig(v) (0xffffffffu/(v))
static int16_t rw_distance,xtoviewangleTable[38];
static uint16_t viewangle16,rw_normalangle;
static uint32_t mulu(uint16_t a,uint16_t b){return (uint32_t)a*b;}
'''+table+'\n'+extract(tables,'finesineapprox')+'\n'
for name in ['FixedMul3232','FixedMul3216','FixedApproxDiv']:code+=extract(src,name)+'\n'
fn=extract(src,'R_ScaleFromGlobalAngle')
code+='#undef DOOM_R20_SCALE_MATH\n'+fn.replace('R_ScaleFromGlobalAngle','reference')+'\n'
code+='#define DOOM_R20_SCALE_MATH 1\n'+fn.replace('R_ScaleFromGlobalAngle','candidate')+'\n'
code+='''static uint32_t state=20261017u;
static uint32_t rnd(void){state^=state<<13;state^=state>>17;state^=state<<5;return state;}
int main(void){
 for(unsigned i=0;i<2000000;i++){
  unsigned x=i%38;xtoviewangleTable[x]=(int16_t)((int)(rnd()%16385)-8192);
  viewangle16=(uint16_t)((int)(rnd()%8192)-4096);rw_normalangle=0;
  rw_distance=(int16_t)rnd();
  if(reference(x)!=candidate(x))return 1;
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);c=p/'scale.c';c.write_text(code);exe=p/'scale'
 subprocess.run(['gcc','-O2','-std=gnu11','-iquote',str(root/'src'),str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS M3 integrated scale: 2,000,000 contexts, actual sine table, division and clamps')
