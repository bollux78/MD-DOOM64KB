#!/usr/bin/env python3
"""Host oracle for original R22 76x44 angle-table ROM data co-linked in R46 M2A.
Original has 76 drawable columns but 77 x->angle edge entries.
"""
import subprocess
from pathlib import Path
import tempfile
import re
root=Path(__file__).resolve().parents[2]
a=[int(x) for x in re.findall(r'\d+', (root/'src/r22_viewangletox.h').read_text())]
b=[int(x) for x in re.findall(r'\d+', (root/'src/r22_xtoviewangle.h').read_text())]
assert len(a)==2032 and len(b)==77
assert b[0]==8192 and b[38]==0 and b[76]==57344
assert a[0]==75 and a[-1]==0
src=r"""
#include <stdint.h>
#include <assert.h>
#include "r46_pixel4_projection.h"
static const uint16_t expected_x[77] = {
#include "r22_xtoviewangle.h"
};
static const uint8_t expected_a[2032] = {
#include "r22_viewangletox.h"
};
int main(void){
    assert(R46_P4_ProjectionValidate());
    for(uint16_t x=0;x<=76;x++){
        assert(R46_P4_XToViewAngle(x)==(int16_t)expected_x[x]);
    }
    assert(R46_P4_XToViewAngle(77)==0);
    for(uint16_t v=0;v<4096;v++){
        uint8_t expected=v<1041 ? 76 : (v>=3073 ? 0 : expected_a[v-1041]);
        assert(R46_P4_ViewAngleToX(v)==expected);
    }
    /* Wrap-around of fine angle; clip table itself remains unchanged */
    assert(R46_P4_ViewAngleToX(4096)==R46_P4_ViewAngleToX(0));
    return 0;
}
"""
with tempfile.TemporaryDirectory(prefix='r46-m2a-') as d:
    p=Path(d)/'test.c'
    out=Path(d)/'test'
    p.write_text(src)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
                    '-DDOOM_R46_M2A','-DDOOM_R46_M1B','-DDOOM_R46_M1',
                    '-I'+str(root/'src'),
                    str(root/'src/r46_pixel4_projection.c'),
                    str(p),'-o',str(out)],check=True)
    subprocess.run([str(out)],check=True)
print('R46 M2A PASS: 77 original x-edge entries and 4096 exact viewangletox angles; no WRAM tables')
