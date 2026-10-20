#!/usr/bin/env python3
"""Native sprite rectangle projection edge cases and nonmutation tests."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
source=(root/'src/r46_pixel4_sprite_camera.c').read_text()
assert 'VDP_' not in source and 'MEM_alloc' not in source and 'static uint8_t' not in source
test=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include "r46_pixel4_sprite_camera.h"
#define Q(n) ((int32_t)(n)*65536)
int main(void){
  r46_p4_sprite_rect_t r={1,2,3,4,5},old=r;
  assert(R46_P4_SpriteCameraValidate());
  assert(!R46_P4_ProjectSpriteRect(0,Q(3),Q(4),Q(1),Q(-1),1,&r));
  assert(!memcmp(&r,&old,sizeof r));
  assert(!R46_P4_ProjectSpriteRect(0,Q(1281),Q(4),Q(1),Q(-1),1,&r));
  assert(!R46_P4_ProjectSpriteRect(0,Q(8),0,Q(1),Q(-1),1,&r));
  assert(!R46_P4_ProjectSpriteRect(0,Q(8),Q(4),Q(-1),Q(1),1,&r));
  assert(!R46_P4_ProjectSpriteRect(0,Q(8),Q(4),Q(1),Q(-1),1,0));
  assert(!memcmp(&r,&old,sizeof r));
  assert(R46_P4_ProjectSpriteRect(0,Q(8),Q(4),Q(2),Q(-2),1,&r));
  assert(r.x1==38&&r.x2==56&&r.y1==11&&r.y2==32&&r.depth_units==8);
  assert(R46_P4_ProjectSpriteRect(Q(-30),Q(8),Q(30),Q(2),Q(-2),1,&r));
  assert(r.x1==2&&r.x2==37);
  assert(!R46_P4_ProjectSpriteRect(Q(100),Q(8),Q(4),Q(2),Q(-2),1,&r));
  assert(!R46_P4_ProjectSpriteRect(Q(-100),Q(8),Q(4),Q(2),Q(-2),1,&r));
  assert(R46_P4_ProjectSpriteRect(Q(-2),Q(4),Q(4),Q(2),Q(-2),1,&r));
  assert(r.x1>=2&&r.x2<76&&r.y1>=2&&r.y2<44);
  /* Full legal depth range and extreme camera positions: never OOB. */
  for(int depth=4;depth<=1280;depth+=3)
    for(int tx=-2000;tx<=2000;tx+=17){
      if(R46_P4_ProjectSpriteRect(Q(tx),Q(depth),Q(8),Q(2),Q(-2),1,&r))
        assert(r.x1>=2&&r.x1<=r.x2&&r.x2<76&&
               r.y1>=2&&r.y1<=r.y2&&r.y2<44);
    }
  return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2c-') as d:
    p=Path(d)/'test.c';exe=Path(d)/'test';p.write_text(test)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
      '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-I'+str(root/'src'),
      str(root/'src/r46_pixel4_sprite_camera.c'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M2C P2C PASS: sprite camera clip and depth bounds')
