#!/usr/bin/env python3
"""P2D host C oracle: actor rotation / bounds / rejection nonmutation."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
src=(root/'src/r46_pixel4_sprite_world.c').read_text()
assert 'VDP_' not in src and 'MEM_alloc' not in src and 'static uint8_t' not in src
test=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <limits.h>
#include "r46_pixel4_sprite_world.h"
#define Q(n) ((int32_t)(n)*65536)
int main(void){
    r46_p4_sprite_camera_point_t c={123,456},old=c;
    r46_p4_sprite_rect_t rect={1,2,3,4,5},saved=rect;
    assert(R46_P4_WorldSpriteValidate());
    assert(R46_P4_WorldToCamera(Q(8),0,0,0,Q(1),0,&c));
    assert(c.depth==Q(8)&&c.lateral==0);
    assert(R46_P4_WorldToCamera(0,Q(8),0,0,Q(1),0,&c));
    assert(c.depth==0&&c.lateral==-Q(8));
    assert(R46_P4_WorldToCamera(0,Q(8),0,0,0,Q(1),&c));
    assert(c.depth==Q(8)&&c.lateral==0);
    c=old;
    assert(!R46_P4_WorldToCamera(INT32_MAX,0,INT32_MIN,0,Q(1),0,&c));
    assert(!memcmp(&old,&c,sizeof c));
    assert(!R46_P4_WorldToCamera(0,0,0,0,70000,0,&c));
    assert(!R46_P4_WorldToCamera(0,0,0,0,Q(1),0,0));
    assert(!memcmp(&old,&c,sizeof c));
    assert(R46_P4_ProjectWorldSprite(Q(8),0,0,0,Q(1),0,
       0,Q(4),Q(2),Q(-2),1,&rect));
    assert(rect.x1==38&&rect.x2==56&&rect.y1==11&&rect.y2==32);
    assert(!R46_P4_ProjectWorldSprite(Q(-8),0,0,0,Q(1),0,
       0,Q(4),Q(2),Q(-2),1,&rect));
    rect=saved;
    assert(!R46_P4_ProjectWorldSprite(INT32_MAX,0,INT32_MIN,0,Q(1),0,
       0,Q(4),Q(2),Q(-2),1,&rect));
    assert(!memcmp(&saved,&rect,sizeof rect));
    for(int x=-100;x<=100;x+=5)
      for(int y=-100;y<=100;y+=5){
        if(R46_P4_ProjectWorldSprite(Q(x),Q(y),0,0,Q(1),0,
           0,Q(8),Q(2),Q(-2),1,&rect))
          assert(rect.x1>=2&&rect.x1<=rect.x2&&rect.x2<76&&
                 rect.y1>=2&&rect.y1<=rect.y2&&rect.y2<44);
      }
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2d-') as d:
    p=Path(d)/'test.c';p.write_text(test);exe=Path(d)/'test'
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
      '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-I'+str(root/'src'),
      str(root/'src/r46_pixel4_sprite_camera.c'),
      str(root/'src/r46_pixel4_sprite_world.c'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M2C P2D PASS: world-to-camera and guarded sprite projection')
