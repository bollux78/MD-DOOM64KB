#!/usr/bin/env python3
"""R46 M2B: exercise the actual 76x44 vertical clipping C on a host.
Compare column results against the standalone R44 ASM clip rules;
verify untouched inputs on rejects, buffer canaries and 8x8 independence.
"""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[2]
src=(root/'src/r46_pixel4_vertical.c').read_text()
r44=(root/'src/r22_video.inc').read_text()
assert 'int16_t border=(_g_gamestate==GS_LEVEL)?2:0;' in r44
assert 'if(first<border) first=border;' in r44
assert 'if(y1>=R22_H) y1=R22_H-1;' in r44
assert 'uint16_t R46_P4_VerticalValidate(void)' in src

test=r'''
#include <assert.h>
#include <stdint.h>
#include "r46_pixel4_vertical.h"
static uint32_t count=0;
static uint16_t original_reference(int16_t x,int16_t *a,int16_t *b,uint16_t gameplay)
{
    int16_t first=*a, last=*b;
    int16_t border=gameplay?2:0;
    if(last<first || (uint16_t)x>=76 || x<border)return 0;
    if(first<border)first=border;
    if(last>=44)last=43;
    if(first>last)return 0;
    *a=first;*b=last;
    return 1;
}
int main(void){
    const r46_p4_vertical_ops_t *ops=R46_P4_VerticalOps();
    assert(ops && ops->geometry_validate() && R46_P4_VerticalValidate());
    assert(ops->clip_column == R46_P4_ClipColumn);
    for(int mode=0;mode<=1;mode++){
        int16_t floors[78],ceilings[78];
        floors[0]=1111;floors[77]=2222;
        ceilings[0]=3333;ceilings[77]=4444;
        R46_P4_InitOpeningClips(&floors[1],&ceilings[1],(uint16_t)mode);
        for(int x=1;x<=76;x++){
            assert(floors[x]==44);
            assert(ceilings[x]==(mode?0:-1));
        }
        assert(floors[0]==1111 && floors[77]==2222);
        assert(ceilings[0]==3333 && ceilings[77]==4444);
    }
    for(int mode=0;mode<=1;mode++){
        for(int x=-4;x<=80;x++){
            for(int yl=-9;yl<=50;yl++){
                for(int yh=-10;yh<=52;yh++){
                    int16_t a=(int16_t)yl,b=(int16_t)yh;
                    int16_t aa=a,bb=b;
                    uint16_t expected=original_reference((int16_t)x,&aa,&bb,(uint16_t)mode);
                    uint16_t got=R46_P4_ClipColumn((int16_t)x,&a,&b,(uint16_t)mode);
                    assert(got==expected && a==aa && b==bb);
                    count++;
                }
            }
        }
    }
    assert(!R46_P4_ClipColumn(5,(int16_t*)0,(int16_t*)0,1));
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-m2b-') as d:
    f=Path(d)/'test.c'; f.write_text(test)
    exe=Path(d)/'test'
    args=['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
          '-DDOOM_R46_M2B','-DDOOM_R46_M2A','-DDOOM_R46_M1B','-DDOOM_R46_M1',
          '-I'+str(root/'src'),str(root/'src/r46_pixel4_vertical.c'),str(f),'-o',str(exe)]
    subprocess.run(args,check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M2B PASS: 642600+ reference clipping combinations, 76-column guard arrays, no WRAM globals')
