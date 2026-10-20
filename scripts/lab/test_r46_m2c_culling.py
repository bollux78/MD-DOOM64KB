#!/usr/bin/env python3
"""R46 M2C/P1: compile actual native C and test plane/BSP/sprite helpers.

Host oracle independently models the same semantics documented in
r_plane.c:R_CheckPlane, r_draw.c:R_CheckBBox and R_ProjectSprite.
M2C/P1 does NOT implement traversal, sprite transformation or a live 4x4
dispatcher; all scratch memory is caller owned.
"""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[2]
src=(root/'src/r46_pixel4_culling.c').read_text()
plane=(root/'src/r_plane.c').read_text()
draw=(root/'src/r_draw.c').read_text()
assert 'pl->top[x] == 0xff' in plane
assert 'memchr(solidcol+sx1, 0, sx2-sx1)' in draw
assert 'vis->scale           = (VIEWWINDOWHEIGHT * FRACUNIT) / (tz >> FRACBITS)' in draw
assert 'vis->fracstep        = tz / (VIEWWINDOWHEIGHT << COLEXTRABITS)' in draw
assert 'static const r46_p4_culling_ops_t' in src
assert 'MEM_alloc' not in src and 'VDP_' not in src

test=r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include "r46_pixel4_culling.h"
static uint32_t rng=0xC0FFEE99UL;
static uint32_t rand32(void){rng=rng*1664525UL+1013904223UL;return rng;}
static uint16_t plane_reference(const uint8_t *top,
      int16_t mi,int16_t ma,int16_t s,int16_t e){
    if(!top||s<0||e>75||s>e)return 0;
    if(mi==76&&ma==-1)return 1;
    if(mi<0||ma>75||mi>ma)return 0;
    int16_t il=(s>mi)?s:mi,ih=(e<ma)?e:ma;
    for(int16_t x=il;x<=ih;x++)if(top[x]!=255)return 0;
    return 1;
}
static uint16_t bsp_reference(const uint8_t *solid,uint16_t l,uint16_t r){
    if(!solid||l>=r||r>76)return 0;
    return memchr(solid+l,0,(size_t)(r-l))!=0;
}
static uint16_t bounds_reference(int16_t *x1,int16_t *x2,uint16_t g){
    int16_t x=*x1, y=*x2, min=g?2:0;
    if(y<x||x>=76||y<min)return 0;
    if(x<min)x=min;
    if(y>75)y=75;
    if(x>y)return 0;
    *x1=x;*x2=y;
    return 1;
}
int main(void){
    const r46_p4_culling_ops_t *ops=R46_P4_CullingOps();
    assert(ops&&R46_P4_CullingValidate());
    assert(ops->plane_can_extend==R46_P4_PlaneCanExtend);
    assert(ops->bsp_any_open==R46_P4_BSPAnyOpen);
    uint8_t plane[80],solid[80];
    for(unsigned iter=0;iter<30000;iter++){
        for(int x=0;x<80;x++)plane[x]=0xA5;
        for(int x=2;x<78;x++)
            plane[x]=(rand32()&3u)==0 ? 0xffu:(uint8_t)(rand32()&0x7fu);
        uint8_t saved[80];memcpy(saved,plane,sizeof(saved));
        int16_t mi=(int16_t)(rand32()%77u);
        int16_t ma=(int16_t)(rand32()%76u);
        if((iter%7)==0){mi=76;ma=-1;}
        else if(mi>ma){int16_t t=mi;mi=ma;ma=t;}
        int16_t st=(int16_t)(rand32()%76u),en=(int16_t)(rand32()%76u);
        if(st>en){int16_t t=st;st=en;en=t;}
        uint16_t exp=plane_reference(plane+2,mi,ma,st,en);
        assert(R46_P4_PlaneCanExtend(plane+2,mi,ma,st,en)==exp);
        assert(!memcmp(plane,saved,sizeof(plane)));
    }
    assert(!R46_P4_PlaneCanExtend(0,0,75,0,75));
    assert(!R46_P4_PlaneCanExtend(plane+2,0,75,0,76));
    assert(!R46_P4_PlaneCanExtend(plane+2,0,75,-1,9));
    for(unsigned iter=0;iter<250;iter++){
        for(unsigned x=0;x<80;x++)solid[x]=0xA5;
        for(unsigned x=2;x<78;x++)solid[x]=((rand32()&7u)==0)?0:1;
        uint8_t saved[80];memcpy(saved,solid,sizeof(saved));
        for(uint16_t l=0;l<=76;l++)
            for(uint16_t r=0;r<=76;r++)
                assert(R46_P4_BSPAnyOpen(solid+2,l,r)==bsp_reference(solid+2,l,r));
        assert(!memcmp(solid,saved,sizeof(solid)));
    }
    assert(!R46_P4_BSPAnyOpen(0,0,76));
    assert(!R46_P4_BSPAnyOpen(solid+2,0,77));
    for(uint16_t g=0;g<=1;g++){
        for(int16_t x=-12;x<=87;x++){
            for(int16_t y=-12;y<=87;y++){
                int16_t a=x,b=y,ca=x,cb=y;
                uint16_t actual=R46_P4_SpriteBounds(&a,&b,g);
                uint16_t expect=bounds_reference(&ca,&cb,g);
                assert(actual==expect && a==ca && b==cb);
            }
        }
    }
    assert(!R46_P4_SpriteBounds(0,0,1));
    for(uint32_t depth=4;depth<=1280;depth++){
        uint32_t values[3]={depth<<16,(depth<<16)+32767u,(depth<<16)+65535u};
        for(unsigned k=0;k<3;k++){
            uint32_t scale=0xDEADBEEFUL;
            uint16_t fracstep=0xBEEFu;
            uint32_t v=values[k];
            uint16_t actual=R46_P4_SpriteDepth(v,&scale,&fracstep);
            /* R_ProjectSprite rejects tz > MAXZ = 1280 * FRACUNIT,
             * including fractional values beyond the last whole unit. */
            if(v>(1280UL<<16)){
                assert(actual==0);
                assert(scale==0xDEADBEEFUL && fracstep==0xBEEFu);
            }else{
                assert(actual==1);
                assert(scale==(44UL*65536UL)/(v>>16));
                assert(fracstep==v/(44UL<<7));
            }
        }
    }
    uint32_t scale=0xDEADBEEF;uint16_t step=0xABCD;
    assert(!R46_P4_SpriteDepth((3UL<<16),&scale,&step));
    assert(!R46_P4_SpriteDepth((1281UL<<16),&scale,&step));
    assert(!R46_P4_SpriteDepth((5UL<<16),0,&step));
    assert(scale==0xDEADBEEF&&step==0xABCD);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-m2c-') as tmp:
    folder=Path(tmp)
    file=folder/'main.c'
    exe=folder/'test'
    file.write_text(test)
    command=['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
       '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-DDOOM_R46_M2A','-DDOOM_R46_M1B',
       '-I'+str(root/'src'),str(root/'src/r46_pixel4_culling.c'),
       str(file),'-o',str(exe)]
    subprocess.run(command,check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M2C/P1 PASS: 30,000 visplanes; 250*77*77 BSP intervals; 20,000 sprite windows; 3831 sprite depths')
