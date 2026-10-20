#!/usr/bin/env python3
"""P2G native C oracles: stable ordering and multi-window post masks."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
for filename in ('r46_pixel4_sprite_order.c','r46_pixel4_sprite_mask.c'):
    source=(root/'src'/filename).read_text()
    assert 'MEM_alloc' not in source and 'VDP_' not in source
test=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "r46_pixel4_sprite_order.h"
#include "r46_pixel4_sprite_mask.h"
static uint32_t state=0x98761234u;
static uint32_t rnd(void){state=state*1664525u+1013904223u;return state;}
static uint64_t seen;
static uint16_t calls;
static void emit(uint16_t x,uint16_t a,uint16_t b,void *ctx){
    assert(ctx==(void*)0x1234&&x==38&&a<=b&&b<44);
    for(uint16_t i=a;i<=b;i++){
        assert(!(seen & (UINT64_C(1)<<i)));
        seen |= UINT64_C(1)<<i;
    }
    calls++;
}
int main(void){
    assert(R46_P4_SpriteOrderValidate()&&R46_P4_SpriteMaskValidate());
    uint16_t depths[128];uint8_t order[128];
    for(int trial=0;trial<3000;trial++){
        uint16_t n=(uint16_t)(rnd()%128)+1;
        for(int i=0;i<n;i++)depths[i]=(uint16_t)(1+(rnd()%40));
        assert(R46_P4_SortSprites(depths,n,order)==n);
        uint8_t counts[128]={0};
        for(int i=0;i<n;i++){
            assert(order[i]<n&&!counts[order[i]]++);
            if(i){
                assert(depths[order[i-1]]>=depths[order[i]]);
                if(depths[order[i-1]]==depths[order[i]])
                    assert(order[i-1]<order[i]);
            }
        }
    }
    for(int i=0;i<128;i++)order[i]=0xAA;
    depths[0]=0;
    assert(!R46_P4_SortSprites(depths,1,order)&&order[0]==0xAA);
    assert(!R46_P4_SortSprites(depths,129,order));
    r46_p4_sprite_rect_t sprite={2,75,2,43,10};
    for(int trial=0;trial<10000;trial++){
        uint64_t mask=((uint64_t)rnd()<<32)|rnd();
        seen=0;calls=0;
        uint16_t result=R46_P4_EmitMaskedPosts(38,&sprite,mask,emit,(void*)0x1234);
        assert(result==calls);
        uint64_t expected=0;
        for(int y=2;y<=43;y++)if(!(mask&(UINT64_C(1)<<y)))
            expected|=UINT64_C(1)<<y;
        assert(seen==expected);
    }
    assert(!R46_P4_EmitMaskedPosts(76,&sprite,0,emit,(void*)0x1234));
    assert(!R46_P4_EmitMaskedPosts(0,&sprite,0,emit,(void*)0x1234));
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-p2g-') as tmp:
    p=Path(tmp)/'main.c';exe=Path(tmp)/'test';p.write_text(test)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-DDOOM_R46_M2C','-DDOOM_R46_M2B','-I'+str(root/'src'),
        str(root/'src/r46_pixel4_sprite_order.c'),
        str(root/'src/r46_pixel4_sprite_mask.c'),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('P2G PASS: 3000 stable-depth sorts; 10000 masked multi-post cases')
