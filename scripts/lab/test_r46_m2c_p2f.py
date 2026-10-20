#!/usr/bin/env python3
"""R46 P2F: execute native C post iteration with independent per-x oracle."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
src=(root/'src/r46_pixel4_sprite_runs.c').read_text()
assert 'MEM_alloc' not in src and 'VDP_' not in src and 'static uint8_t' not in src
test=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include "r46_pixel4_sprite_runs.h"
static uint32_t state=0x7890abcd;
static uint32_t rnd(void){state=1664525u*state+1013904223u;return state;}
static uint16_t seen[76],count;
static void sink(uint16_t x,int16_t y0,int16_t y1,void *ctx){
    assert(ctx==(void*)0x6789);assert(x<76&&y0>=0&&y1<44&&y0<=y1);
    assert(!seen[x]);seen[x]=1;count++;
}
int main(void){
    int16_t ceiling[76],floor[76];
    uint8_t solid[76];uint16_t depth[76];
    r46_p4_sprite_rect_t r={2,75,2,43,10};
    for(int x=0;x<76;x++){ceiling[x]=-1;floor[x]=44;solid[x]=0;depth[x]=0;}
    assert(R46_P4_SpriteRunsValidate());
    assert(R46_P4_EmitSpritePosts(&r,ceiling,floor,solid,depth,sink,
                                  (void*)0x6789)==74);
    assert(count==74 && !seen[0]&&!seen[1] && seen[75]);
    for(unsigned i=0;i<10000;i++){
        for(unsigned x=0;x<76;x++){
            ceiling[x]=(int16_t)(rnd()%45)-1;
            floor[x]=(int16_t)(rnd()%45);
            solid[x]=(uint8_t)(rnd()&1);
            depth[x]=(uint16_t)(rnd()%25);
        }
        memset(seen,0,sizeof seen);count=0;
        uint16_t n=R46_P4_EmitSpritePosts(&r,ceiling,floor,solid,depth,
                                         sink,(void*)0x6789);
        assert(n==count);
        for(unsigned x=0;x<76;x++){
            int y0=r.y1>ceiling[x]?r.y1:ceiling[x]+1;
            int y1=r.y2<floor[x]?r.y2:floor[x]-1;
            int occluded=solid[x] && depth[x] && depth[x]<r.depth_units;
            int expected=(x>=2)&&!occluded&&y0<=y1;
            assert(seen[x]==(uint16_t)expected);
        }
    }
    count=0;memset(seen,0,sizeof seen);
    r.x2=76;
    assert(!R46_P4_EmitSpritePosts(&r,ceiling,floor,solid,depth,
                                  sink,(void*)0x6789));
    assert(count==0);
    r.x2=75;r.depth_units=0;
    assert(!R46_P4_EmitSpritePosts(&r,ceiling,floor,solid,depth,
                                  sink,(void*)0x6789));
    assert(count==0);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2f-') as d:
    p=Path(d)/'test.c';p.write_text(test);exe=Path(d)/'test'
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
       '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-I'+str(root/'src'),
       str(root/'src/r46_pixel4_sprite_occlusion.c'),
       str(root/'src/r46_pixel4_sprite_runs.c'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M2C/P2F PASS: 10,000 random 76-column sprite scans')
