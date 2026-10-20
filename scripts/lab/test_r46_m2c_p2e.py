#!/usr/bin/env python3
"""R46 P2E: actual C 76-column sprite post clipping and wall occlusion."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/r46_pixel4_sprite_occlusion.c').read_text()
assert 'VDP_' not in source and 'MEM_alloc' not in source
test=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include "r46_pixel4_sprite_occlusion.h"
static uint32_t seed=0x12345678u;
static uint32_t rnd(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){
    int16_t ceil[78],floor[78];uint8_t solid[78];uint16_t wall[78];
    for(int x=0;x<78;x++){ceil[x]=-1;floor[x]=44;solid[x]=0;wall[x]=0;}
    r46_p4_sprite_rect_t sprite={2,75,2,43,10};
    r46_p4_sprite_post_t out={12,13},previous=out;
    assert(R46_P4_SpriteOcclusionValidate());
    assert(R46_P4_SpriteVisiblePost(3,&sprite,ceil+1,floor+1,
                                   solid+1,wall+1,&out));
    assert(out.top==2&&out.bottom==43);
    ceil[4]=9;floor[4]=35;
    assert(R46_P4_SpriteVisiblePost(3,&sprite,ceil+1,floor+1,
                                   solid+1,wall+1,&out));
    assert(out.top==10&&out.bottom==34);
    solid[4]=1;wall[4]=9;
    previous=out;
    assert(!R46_P4_SpriteVisiblePost(3,&sprite,ceil+1,floor+1,
                                    solid+1,wall+1,&out));
    assert(!memcmp(&previous,&out,sizeof out));
    wall[4]=10;
    assert(R46_P4_SpriteVisiblePost(3,&sprite,ceil+1,floor+1,
                                   solid+1,wall+1,&out));
    assert(out.top==10&&out.bottom==34);
    assert(!R46_P4_SpriteVisiblePost(76,&sprite,ceil+1,floor+1,
                                    solid+1,wall+1,&out));
    assert(!R46_P4_SpriteVisiblePost(1,&sprite,ceil+1,floor+1,
                                    solid+1,wall+1,&out));
    assert(ceil[0]==-1&&ceil[77]==-1&&floor[0]==44&&floor[77]==44);
    for(int i=0;i<30000;i++){
        uint16_t x=(uint16_t)(rnd()%76u);
        int16_t c=(int16_t)(rnd()%45u)-1;
        int16_t f=(int16_t)(rnd()%45u);
        ceil[x+1]=c;floor[x+1]=f;
        solid[x+1]=(uint8_t)(rnd()&1u);
        wall[x+1]=(uint16_t)(rnd()%20u);
        uint16_t res=R46_P4_SpriteVisiblePost(x,&sprite,ceil+1,
                                   floor+1,solid+1,wall+1,&out);
        int expected=(x>=2 && !(solid[x+1]&&wall[x+1]&&wall[x+1]<10));
        int top=2>c?2:c+1,bottom=43<f?43:f-1;
        expected=expected&&top<=bottom;
        assert(res==(uint16_t)expected);
        if(res)assert(out.top==top&&out.bottom==bottom);
    }
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2e-') as d:
    p=Path(d)/'test.c';p.write_text(test);exe=Path(d)/'test'
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
      '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-I'+str(root/'src'),
      str(root/'src/r46_pixel4_sprite_occlusion.c'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M2C P2E PASS: 30,000 sprite post occlusion/clipping tests')
