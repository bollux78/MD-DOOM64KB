#!/usr/bin/env python3
"""P2I: actual-C packed framebuffer and composited P2H scene host oracle."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
for name in ('r46_pixel4_raster.c','r46_pixel4_composite.c'):
    source=(root/'src'/name).read_text()
    assert 'VDP_' not in source and 'MEM_alloc' not in source
    assert '_s_screen' not in source.replace('never _s_screen','')
test=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "r46_pixel4_composite.h"
static uint64_t lookup(uint16_t id,uint16_t x,void *ctx){
    assert(ctx==(void *)0x1234 && x==6 && id<2);
    return id==0 ? ((uint64_t)1<<4) : 0;
}
int main(void){
    assert(R46_P4_RasterValidate() && R46_P4_CompositeValidate());
    uint8_t mem[1674]; memset(mem,0xab,sizeof mem);
    uint8_t *frame=mem+1;
    assert(!R46_P4_ClearTarget(frame,1671,1,2));
    assert(mem[1]==0xab);
    assert(R46_P4_ClearTarget(frame,1672,1,2));
    for(int i=0;i<76;i++)assert(frame[i]==0xab);
    for(int i=76;i<1672;i++)assert(frame[i]==0x11);
    assert(mem[0]==0xab && mem[1673]==0xab);
    assert(R46_P4_FillColumn(frame,1672,6,3,5,10));
    assert(R46_P4_ReadSample(frame,1672,6,3)==10);
    assert(R46_P4_ReadSample(frame,1672,7,3)==1);
    assert(R46_P4_FillRow(frame,1672,8,5,6,14));
    assert(R46_P4_ReadSample(frame,1672,5,8)==14);
    assert(R46_P4_ReadSample(frame,1672,6,8)==14);
    assert(R46_P4_ReadSample(frame,1672,4,8)==1);
    assert(R46_P4_ReadSample(frame,1672,7,8)==1);
    assert(!R46_P4_FillRow(frame,1672,44,0,1,2));
    assert(!R46_P4_FillColumn(frame,1672,76,0,1,2));
    assert(R46_P4_ReadSample(frame,1672,76,0)==255);
    r46_p4_plane_window_t p;
    R46_P4_PlaneInit(&p);
    assert(R46_P4_PlaneJoin(&p,4,8));
    for(uint16_t x=4;x<=8;x++)assert(R46_P4_PlaneSetColumn(&p,x,3,3));
    uint8_t starts[44];
    r46_p4_sprite_rect_t sprites[2]={
        {6,6,2,7,8},{6,6,2,7,12}
    };
    uint16_t depths[2]={8,12};
    uint8_t colors[2]={10,5},indices[2]={255,255};
    r46_p4_composite_stats_t stats={99,99};
    assert(R46_P4_ComposePreview(frame,1672,&p,starts,1,3,2,
        sprites,depths,colors,2,indices,lookup,(void *)0x1234,&stats));
    assert(stats.plane_spans==1 && stats.sprite_posts==3);
    assert(indices[0]==1 && indices[1]==0);
    assert(R46_P4_ReadSample(frame,1672,4,3)==3);
    assert(R46_P4_ReadSample(frame,1672,8,3)==3);
    assert(R46_P4_ReadSample(frame,1672,3,3)==1);
    assert(R46_P4_ReadSample(frame,1672,6,2)==10);
    assert(R46_P4_ReadSample(frame,1672,6,3)==10);
    assert(R46_P4_ReadSample(frame,1672,6,4)==5);
    assert(R46_P4_ReadSample(frame,1672,6,5)==10);
    assert(R46_P4_ReadSample(frame,1672,7,4)==1);
    assert(mem[0]==0xab && mem[1673]==0xab);
    for(int i=0;i<76;i++)assert(frame[i]==0xab);
    uint8_t backup[1672];memcpy(backup,frame,sizeof backup);
    stats.plane_spans=77;stats.sprite_posts=88;
    sprites[1].x2=76;
    assert(!R46_P4_ComposePreview(frame,1672,&p,starts,1,3,2,
        sprites,depths,colors,2,indices,lookup,(void *)0x1234,&stats));
    assert(!memcmp(backup,frame,sizeof backup));
    assert(stats.plane_spans==77 && stats.sprite_posts==88);
    sprites[1].x2=6;
    assert(!R46_P4_ComposePreview(frame,1671,&p,starts,1,3,2,
        sprites,depths,colors,2,indices,lookup,(void *)0x1234,&stats));
    assert(!memcmp(backup,frame,sizeof backup));
    assert(R46_P4_ComposePreview(frame,1672,&p,starts,2,3,2,
        0,0,0,0,0,0,0,&stats));
    assert(stats.plane_spans==1 && stats.sprite_posts==0);
    assert(R46_P4_ReadSample(frame,1672,6,3)==3);
    assert(R46_P4_ReadSample(frame,1672,6,4)==2);
    for(int i=0;i<76;i++)assert(frame[i]==0xab);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2i-') as d:
    p=Path(d)/'test.c';exe=Path(d)/'test';p.write_text(test)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
       '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-I'+str(root/'src'),
       str(root/'src/r46_pixel4_raster.c'),
       str(root/'src/r46_pixel4_spans.c'),
       str(root/'src/r46_pixel4_plane_owner.c'),
       str(root/'src/r46_pixel4_sprite_order.c'),
       str(root/'src/r46_pixel4_sprite_mask.c'),
       str(root/'src/r46_pixel4_pipeline.c'),
       str(root/'src/r46_pixel4_composite.c'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 P2I PASS: packed 4bpp nibble integrity, plane+sprite order, topbar guards')
