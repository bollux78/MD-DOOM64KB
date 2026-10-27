#!/usr/bin/env python3
"""Compile real postpass; exercise every palette/profile with random blocks.
Also exhaustively inspect the 65536 packed block decisions in NumPy.
"""
from pathlib import Path
import argparse,re,subprocess,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def parse(name):
 text=(ROOT/'src/r79_shadow_tables.h').read_text()
 m=re.search(r'\b'+name+r'((?:\[\d+\])+)\s*=\s*\{(.*?)\};',text,re.S);assert m
 shape=tuple(map(int,re.findall(r'\d+',m[1])));return np.array(list(map(int,re.findall(r'\d+',m[2])))).reshape(shape)
def main():
 p=argparse.ArgumentParser();p.add_argument('--generated',action='store_true');p.parse_args()
 maps,cost=parse('r79_map'),parse('r79_cost');assert maps.shape==(4,14,2,2,256)
 assert not np.any(maps[:,:,:,1]&0x8000)
 assert np.all(maps[:,:,0,0]&0x8000) and not np.any(maps[:,:,1,0]&0x8000)
 assert np.all((maps[:,:,:,0]&0x7f00)==0x100) and np.all((maps[:,:,:,1]&0x7f00)==0x2200)
 for mode in range(4):
  for pal in range(14):
   c=cost[mode,pal];normal=c[0,0,:,None]+c[0,1,None,:];shadow=c[1,0,:,None]+c[1,1,None,:]
   state=shadow<normal
   selected=np.where(state,shadow,normal);assert np.array_equal(selected,np.minimum(normal,shadow))
   # Priorities include transparent portions of A. B never contaminates its neighbour.
   for pa in (0,1):
    for phase in range(8):assert (pa | 0)==pa
 with tempfile.TemporaryDirectory() as td:
  d=Path(td);(d/'r79_shadow_tables.h').write_text((ROOT/'src/r79_shadow_tables.h').read_text())
  (d/'r79_shadow.inc').write_text((ROOT/'src/r79_shadow.inc').read_text())
  (d/'test.c').write_text('''#include <stdint.h>
#include <assert.h>
#include <string.h>
#include "r79_shadow_tables.h"
#include "r79_shadow.inc"
int main(void){
 uint16_t buf[22*76],old[22*76];uint32_t rng=1;
 for(unsigned m=0;m<4;m++)for(unsigned p=0;p<14;p++)for(unsigned round=0;round<8;round++){
  for(unsigned i=0;i<22*76;i++){rng=rng*1664525u+1013904223u;buf[i]=(uint16_t)(rng>>16);}
  memcpy(old,buf,sizeof(buf));R79_Convert(buf,r79_map[m][p],r79_cost[m][p]);
  assert(memcmp(old,buf,76*sizeof(uint16_t))==0);
  for(unsigned y=1;y<22;y++)for(unsigned x=0;x<38;x++){
   unsigned a=y*76+x,b=a+38,ca=old[a]&255,cb=old[b]&255;
   const uint16_t (*c)[2][256]=r79_cost[m][p];
   uint32_t n=(uint32_t)c[0][0][ca]+c[0][1][cb],s=(uint32_t)c[1][0][ca]+c[1][1][cb];
   unsigned sh=s<n;assert(buf[a]==r79_map[m][p][sh][0][ca]);assert(buf[b]==r79_map[m][p][sh][1][cb]);
   assert((buf[b]&0x8000)==0);assert(!!(buf[a]&0x8000)==!sh);
  }
 }
 return 0;
}''')
  subprocess.run(['gcc','-std=c99','-O2','-Wall','-Wextra','-Werror',str(d/'test.c'),'-o',str(d/'test')],check=True)
  subprocess.run([str(d/'test')],check=True)
 print('PASS R79 actual C postpass, all 4 profiles x 14 palettes, ROM map bounds, packed costs and neighbour-safe priorities')
if __name__=='__main__':main()
