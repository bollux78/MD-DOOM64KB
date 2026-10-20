#!/usr/bin/env python3
"""P2A host oracle: actual C native 76x44 transitions and solid masks."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/r46_pixel4_spans.c').read_text()
assert 'static uint8_t' not in source and 'VDP_' not in source
h=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "r46_pixel4_spans.h"
static uint16_t calls;
static uint16_t row,x0,x1;
static void emit(uint16_t y,uint16_t a,uint16_t b,void *ctx){
    assert(ctx==(void*)0x1234);assert(y<44&&a<=b&&b<76);
    calls++;row=y;x0=a;x1=b;
}
int main(void){
    uint8_t starts[46],solid[78];
    memset(starts,0xa5,sizeof starts);memset(solid,0xa5,sizeof solid);
    R46_P4_SpansClear(starts+1,solid+1);
    assert(starts[0]==0xa5&&starts[45]==0xa5);
    assert(solid[0]==0xa5&&solid[77]==0xa5);
    for(int i=1;i<45;i++)assert(starts[i]==255);
    for(int i=1;i<77;i++)assert(solid[i]==0);
    assert(R46_P4_SpansValidate());
    assert(R46_P4_MarkSolid(solid+1,-20,5)==5);
    assert(R46_P4_MarkSolid(solid+1,2,9)==4);
    assert(R46_P4_MarkSolid(solid+1,75,90)==1);
    assert(R46_P4_MarkSolid(solid+1,76,90)==0);
    assert(R46_P4_MarkSolid(solid+1,10,2)==0);
    assert(solid[0]==0xa5&&solid[77]==0xa5);
    /* Open row 3 at x=4, close it at x=9. */
    assert(R46_P4_MakeSpans(starts+1,4,44,0,3,3,emit,(void*)0x1234)==0);
    assert(starts[4]==4);
    assert(R46_P4_MakeSpans(starts+1,9,3,3,44,0,emit,(void*)0x1234)==1);
    assert(calls==1&&row==3&&x0==4&&x1==8);
    /* Two-row interval and closing boundary x=76. */
    assert(R46_P4_MakeSpans(starts+1,20,44,0,10,11,emit,(void*)0x1234)==0);
    assert(R46_P4_MakeSpans(starts+1,76,10,11,44,0,emit,(void*)0x1234)==2);
    assert(calls==3);
    assert(!R46_P4_MakeSpans(starts+1,77,0,0,1,1,emit,(void*)0x1234));
    assert(!R46_P4_MakeSpans(starts+1,30,0,44,1,1,emit,(void*)0x1234));
    assert(!R46_P4_MakeSpans(starts+1,30,0,1,1,44,emit,(void*)0x1234));
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2a-') as d:
    src=Path(d)/'test.c';exe=Path(d)/'test'
    src.write_text(h)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-DDOOM_R46_M2C','-DDOOM_R46_M2B',
        '-I'+str(root/'src'),str(root/'src/r46_pixel4_spans.c'),
        str(src),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('M2C/P2A PASS: native 76x44 spans, bound checks, BSP solid ranges, 0 static scratch')
