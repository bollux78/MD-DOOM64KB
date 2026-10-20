#!/usr/bin/env python3
"""R46 P2H: host-compile the *actual* integrated 76x44 geometry kernels."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'src/r46_pixel4_pipeline.c').read_text()
assert 'VDP_' not in source and 'MEM_alloc' not in source and 'static uint8_t' not in source
test=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "r46_pixel4_pipeline.h"
static int count_plane=0,count_sprite=0;
static uint16_t last_id=999,seen_order[3],seen_count=0;
static void emit_span(uint16_t y,uint16_t x0,uint16_t x1,void *ctx){
    assert(ctx==(void*)0x1234);assert(y==3 && x0==4 && x1==8);
    count_plane++;
}
static uint64_t lookup(uint16_t id,uint16_t x,void *ctx){
    assert(ctx==(void*)0x1234);assert(x==38);
    return id==0 ? ((uint64_t)1<<5) : 0;
}
static void emit_post(uint16_t id,uint16_t x,uint16_t y0,uint16_t y1,void *ctx){
    assert(ctx==(void*)0x1234 && x==38);
    if(id!=last_id){
        assert(seen_count<3);
        seen_order[seen_count++]=id;last_id=id;
    }
    if(id==0)assert((y0==2&&y1==4)||(y0==6&&y1==9));
    if(id==1)assert(y0==2&&y1==9);
    count_sprite++;
}
int main(void){
    assert(R46_P4_PipelineValidate());
    r46_p4_plane_window_t plane;
    uint8_t starts[44];
    R46_P4_PlaneInit(&plane);
    memset(starts,255,sizeof starts);
    assert(R46_P4_PlaneJoin(&plane,4,8));
    for(int i=4;i<=8;i++)
        assert(R46_P4_PlaneSetColumn(&plane,(uint16_t)i,3,3));
    /* A filled horizontal strip from x4 to x8 generates one row span. */
    assert(R46_P4_SweepPlane(&plane,starts,emit_span,(void*)0x1234)==1);
    assert(count_plane==1);
    /* Reject malformed plane before issuing callbacks. */
    plane.top[6]=44;
    assert(!R46_P4_SweepPlane(&plane,starts,emit_span,(void*)0x1234));
    assert(count_plane==1);
    r46_p4_sprite_rect_t sprites[2]={{38,38,2,9,8},{38,38,2,9,12}};
    uint16_t depth[2]={8,12};
    uint8_t order[2]={255,255};
    assert(R46_P4_EmitOrderedSpriteScene(sprites,depth,2,order,
                lookup,emit_post,(void*)0x1234)==3);
    assert(order[0]==1&&order[1]==0);
    assert(seen_count==2&&seen_order[0]==1&&seen_order[1]==0);
    assert(count_sprite==3);
    sprites[1].x2=76;
    assert(!R46_P4_EmitOrderedSpriteScene(sprites,depth,2,order,
                lookup,emit_post,(void*)0x1234));
    assert(count_sprite==3);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2h-') as d:
    p=Path(d)/'test.c';p.write_text(test);exe=Path(d)/'test'
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
       '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-I'+str(root/'src'),
       str(root/'src/r46_pixel4_spans.c'),
       str(root/'src/r46_pixel4_plane_owner.c'),
       str(root/'src/r46_pixel4_sprite_order.c'),
       str(root/'src/r46_pixel4_sprite_mask.c'),
       str(root/'src/r46_pixel4_pipeline.c'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 P2H PASS: native plane-to-span and ordered masked-sprite integration')
