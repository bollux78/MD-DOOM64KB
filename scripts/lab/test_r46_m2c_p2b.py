#!/usr/bin/env python3
"""Native C guarded plane + BSP maximal visible range oracle."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/r46_pixel4_plane_owner.c').read_text()
assert 'static uint8_t' not in source and 'MEM_alloc' not in source and 'VDP_' not in source
test=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include "r46_pixel4_plane_owner.h"
static uint32_t state=0x1234abcd;
static uint32_t rnd(void){state=state*1664525u+1013904223u;return state;}
static uint16_t spans, covered[76];
static void out(uint16_t a,uint16_t b,void *context){
    assert(context==(void*)0xabc);assert(a<b&&b<=76);
    for(uint16_t x=a;x<b;x++){assert(!covered[x]);covered[x]=1;}
    spans++;
}
int main(void){
    r46_p4_plane_window_t p;R46_P4_PlaneInit(&p);
    assert(R46_P4_PlaneOwnerValidate());
    assert(p.minx==76&&p.maxx==-1&&p.top[0]==255&&p.top[77]==255);
    assert(!R46_P4_PlaneJoin(&p,-1,3));
    assert(!R46_P4_PlaneJoin(&p,0,76));
    assert(R46_P4_PlaneJoin(&p,4,12));
    assert(R46_P4_PlaneSetColumn(&p,5,3,9));
    assert(!R46_P4_PlaneJoin(&p,5,17));
    assert(p.minx==4&&p.maxx==12);
    assert(R46_P4_PlaneJoin(&p,11,20));
    assert(p.minx==4&&p.maxx==20);
    assert(!R46_P4_PlaneSetColumn(&p,20,44,44));
    assert(!R46_P4_PlaneSetColumn(&p,76,1,2));
    assert(p.top[6]==3&&p.bottom[6]==9);
    assert(p.top[0]==255&&p.top[77]==255);
    uint8_t guard[78];memset(guard,0xa5,sizeof guard);
    for(uint32_t i=0;i<10000;i++){
        uint8_t solid[76];
        for(uint16_t x=0;x<76;x++)solid[x]=(rnd()&7u)==0?0:1;
        uint16_t a=rnd()%76u,b=a+1+(rnd()%(76-a));
        memset(covered,0,sizeof covered);spans=0;
        uint16_t n=R46_P4_BSPOpenRuns(solid,a,b,out,(void*)0xabc);
        assert(n==spans);
        for(uint16_t x=0;x<76;x++)
            assert(covered[x]==(uint16_t)(x>=a&&x<b&&!solid[x]));
    }
    assert(!R46_P4_BSPOpenRuns(guard,20,19,out,(void*)0xabc));
    assert(!R46_P4_BSPOpenRuns(guard,0,77,out,(void*)0xabc));
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2b-') as d:
    src=Path(d)/'test.c';exe=Path(d)/'test';src.write_text(test)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
      '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-I'+str(root/'src'),
      str(root/'src/r46_pixel4_plane_owner.c'),str(src),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M2C P2B PASS: guarded visplanes and 10,000 BSP visible-run scenarios')
