#!/usr/bin/env python3
"""Exact R79 normal-palette decisions precomputed for A2/L3; 512 KiB ROM."""
from pathlib import Path
import re,json,subprocess,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def arr(text,name):
 m=re.search(r'\b'+name+r'((?:\[\d+\])+)\s*=\s*\{(.*?)\};',text,re.S);assert m,name
 shape=tuple(map(int,re.findall(r'\d+',m[1])));return np.array(list(map(int,re.findall(r'\d+',m[2]))),dtype=np.uint32).reshape(shape)
def emit(name,a,typ):
 def nest(v):return '{'+','.join(nest(x) if np.ndim(x) else str(int(x))+'u' for x in v)+'}'
 return 'static const '+typ+' '+name+''.join('['+str(x)+']' for x in a.shape)+'='+nest(a)+';\n'
def joint(maps,cost):
 ca=np.arange(256)[:,None];cb=np.arange(256)[None,:]
 state=cost[1,0,:,None]+cost[1,1,None,:] < cost[0,0,:,None]+cost[0,1,None,:]
 return ((maps[state.astype(int),0,ca].astype(np.uint32)<<16)|maps[state.astype(int),1,cb]).reshape(-1)
def main():
 p=ROOT/'src/r79_shadow_tables.h';s=p.read_text();maps=arr(s,'r79_map')[[1,2]];cost=arr(s,'r79_cost')[[1,2]];pal=arr(s,'r79_pal')[[1,2]]
 fast=np.stack([joint(maps[i,0],cost[i,0]) for i in range(2)])
 # Independently check every pair, including transparent codes and exact ties.
 for mode in range(2):
  for ca in range(256):
   for cb in range(256):
    c=cost[mode,0];state=int(int(c[1,0,ca])+int(c[1,1,cb]) < int(c[0,0,ca])+int(c[0,1,cb]))
    expected=(int(maps[mode,0,state,0,ca])<<16)|int(maps[mode,0,state,1,cb])
    assert int(fast[mode,ca*256+cb])==expected
 p.write_text(emit('r79_pal',pal,'uint16_t')+emit('r79_map',maps,'uint16_t')+emit('r79_cost',cost,'uint16_t')+emit('r91_joint',fast,'uint32_t'))
 # Compile and exercise the production pass, retaining top row and buffer guards.
 with tempfile.TemporaryDirectory() as td:
  d=Path(td);c=d/'test.c';c.write_text('#include <stdint.h>\n#include <assert.h>\n#include <string.h>\n'+p.read_text()+(ROOT/'src/r79_shadow.inc').read_text()+(ROOT/'src/r91_shadow.inc').read_text()+'''\nint main(void){uint16_t a[1674],b[1674];uint32_t r=1;for(int m=0;m<2;m++)for(int k=0;k<40;k++){for(int i=0;i<1674;i++){r=r*1664525u+1013904223u;a[i]=b[i]=(uint16_t)(r>>16);}R79_Convert(a+1,r79_map[m][0],r79_cost[m][0]);R91_ConvertFast(b+1,r91_joint[m]);assert(memcmp(a,b,sizeof a)==0);}return 0;}''')
  subprocess.run(['cc','-O2',str(c),'-o',str(d/'test')],check=True);subprocess.run([str(d/'test')],check=True)
 report={'profiles':['A2','L3'],'joint_table_bytes':int(fast.nbytes),'exhaustive_blocks':131072,'actual_c_frame_comparisons':80,'palette_effects':'original R79 fallback for p>0','extra_wram':0,'limitation':'final conversion pass retained; same joint block decisions/visual compromises as R79'}
 (ROOT/'src/r91_shadow_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
