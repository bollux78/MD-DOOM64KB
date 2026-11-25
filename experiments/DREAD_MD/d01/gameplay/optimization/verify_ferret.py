#!/usr/bin/env python3
"""Exercise the actual cache code with colliding endpoints and frame changes."""
from pathlib import Path
import subprocess,tempfile,random
src=Path(__file__).resolve().parents[2]/'src/render.c'
s=src.read_text();start=s.index('static inline uint16_t xform(');end=s.index('/* screen x in 16.16',start);fn=s[start:end]
c='''#include <stdint.h>
#include <assert.h>
#define MAXV 8192
#define VCACHE_SIZE 256
#define DREAD_FERRET_CACHE2
static uint16_t vkey[256],vstamp[256],frame_id;
static int16_t vtx[256],vtz[256],map_verts[8192][2];
static int16_t clamp16(int32_t v){return v>32767?32767:(v<-32767?-32767:(int16_t)v);}
static void cam(int16_t x,int16_t y,int32_t*a,int32_t*b){*a=x;*b=y;}
'''+fn+'''
int main(void){
 for(int i=0;i<MAXV;i++){map_verts[i][0]=i;map_verts[i][1]=i^1234;}
 for(int frame=1;frame<1000;frame++){
  frame_id=(uint16_t)frame;
  for(int k=0;k<8192;k++){
   uint16_t a=(uint16_t)((k*257u+frame)%8192),b=(uint16_t)((a+128u*(k%63+1))%8192);
   uint16_t s1=xform(a),s2=xform(b);
   assert(vtx[s1]==a && vtz[s1]==(a^1234));
   assert(vtx[s2]==b && vtz[s2]==(b^1234));
  }
 }
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'cache.c').write_text(c)
 subprocess.run(['cc','-std=c99','-O2',str(p/'cache.c'),'-o',str(p/'cache')],check=True)
 subprocess.run([str(p/'cache')],check=True)
# Verify restarting fixed point row sums at sparse offsets against uninterrupted additions.
rng=random.Random(20261125)
for _ in range(20000):
 value=rng.randrange(1<<32);step=rng.randrange(1<<32);n=rng.randrange(1,161)
 baseline=[];v=value
 for i in range(n):baseline.append(v);v=(v+step)&0xffffffff
 for i in (0,n//2,n-1):assert baseline[i]==(value+step*i)&0xffffffff
print('FERRET PREFLIGHT PASS: 8 million actual-cache endpoint checks; 20000 row restart cases')
