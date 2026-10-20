#!/usr/bin/env python3
"""R46 M3A: actual host C owner barrier and pixel4->VRAM packing parity."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
for name in ('r46_m3_owner.c','r46_m3_tiles.c'):
    source=(root/'src'/name).read_text()
    assert 'MEM_alloc' not in source and 'VDP_' not in source
    assert 'extern uint16_t _s_screen' not in source and '_s_screen[' not in source
test=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "r46_m3_owner.h"
#include "r46_m3_tiles.h"
#include "r46_pixel4_vram.h"
uint16_t _s_screen[38*28];
static uint32_t state=0x1234abcdu;
static uint32_t rnd(void){state=state*1664525u+1013904223u;return state;}
int main(void){
    assert(R46_M3_OwnerValidate());
    assert(R46_M3_TilesValidate());
    assert(R46_P4_VramValidate());
    r46_m3_owner_t owner;
    R46_M3_OwnerInit(&owner);
    assert(R46_M3_MayWrite(&owner,R46_M3_CELL));
    assert(!R46_M3_MayWrite(&owner,R46_M3_PIXEL4));
    assert(!R46_M3_Commit(&owner));
    assert(!R46_M3_AckQuiesce(&owner,R46_M3_DMA_DRAINED));
    assert(R46_M3_Request(&owner,R46_M3_PIXEL4));
    assert(!R46_M3_Request(&owner,R46_M3_PIXEL4));
    assert(!R46_M3_MayWrite(&owner,R46_M3_CELL));
    assert(!R46_M3_MayWrite(&owner,R46_M3_PIXEL4));
    assert(!R46_M3_AckReconfigure(&owner,R46_M3_VRAM_READY));
    assert(!R46_M3_AckQuiesce(&owner,4));
    assert(R46_M3_AckQuiesce(&owner,R46_M3_IRQ_DISABLED));
    assert(owner.phase==R46_M3_QUIESCE);
    assert(R46_M3_AbortQuiesce(&owner));
    assert(R46_M3_MayWrite(&owner,R46_M3_CELL));
    assert(R46_M3_Request(&owner,R46_M3_PIXEL4));
    assert(R46_M3_AckQuiesce(&owner,R46_M3_DMA_DRAINED));
    assert(owner.phase==R46_M3_QUIESCE);
    assert(R46_M3_AckQuiesce(&owner,R46_M3_IRQ_DISABLED));
    assert(owner.phase==R46_M3_RECONFIGURE);
    assert(!R46_M3_AbortQuiesce(&owner));
    assert(!R46_M3_AckQuiesce(&owner,R46_M3_DMA_DRAINED));
    assert(!R46_M3_Commit(&owner));
    assert(R46_M3_AckReconfigure(&owner,R46_M3_VRAM_READY));
    assert(R46_M3_AckReconfigure(&owner,R46_M3_CRAM_READY));
    assert(!R46_M3_Commit(&owner));
    uint8_t *packed=(uint8_t *)(void*)_s_screen;
    uint32_t untouched[8];
    for(unsigned i=0;i<8;i++)untouched[i]=0xa5a5a5a5u;
    assert(R46_M3_PackOwned(&owner,packed,1672,0,0,1,untouched)==0);
    for(unsigned i=0;i<8;i++)assert(untouched[i]==0xa5a5a5a5u);
    assert(R46_M3_AckReconfigure(&owner,R46_M3_MAP_READY));
    assert(R46_M3_Commit(&owner));
    assert(owner.owner==R46_M3_PIXEL4&&owner.phase==R46_M3_ACTIVE);
    assert(R46_M3_MayWrite(&owner,R46_M3_PIXEL4));
    assert(!R46_M3_MayWrite(&owner,R46_M3_CELL));
    assert(!R46_M3_Request(&owner,R46_M3_PIXEL4));
    assert(R46_M3_TileAt(0,1672,0,0,1)==65535u);
    assert(R46_M3_TileAt(packed,1671,0,0,1)==65535u);
    assert(R46_M3_TileAt(packed,1672,2,0,1)==65535u);
    assert(R46_M3_TileAt(packed,1672,0,38,1)==65535u);
    assert(R46_M3_TileAt(packed,1672,0,0,0)==65535u);
    assert(R46_M3_TileAt(packed,1672,0,0,22)==65535u);
    uint16_t sentinel_map[38];
    for(unsigned i=0;i<38;i++)sentinel_map[i]=0xbeefu;
    assert(!R46_M3_MapRow(packed,1671,0,1,sentinel_map));
    for(unsigned i=0;i<38;i++)assert(sentinel_map[i]==0xbeefu);
    for(unsigned pass=0;pass<28;pass++){
        for(unsigned i=0;i<sizeof _s_screen;i++)packed[i]=(uint8_t)rnd();
        if(pass==0)memset(packed,0,1672);
        if(pass==1)memset(packed,0xff,1672);
        if(pass==2)memset(packed,0x22,1672);
        if(pass==3)memset(packed,0xf0,1672);
        uint8_t snapshot[sizeof _s_screen];
        memcpy(snapshot,packed,sizeof snapshot);
        for(unsigned bank=0;bank<2;bank++){
            for(unsigned row=1;row<=21;row++){
                uint16_t m3map[38],m1bmap[38];
                assert(R46_M3_MapRow(packed,1672,bank,row,m3map)==38);
                assert(R46_P4_MapRow(bank,row,m1bmap)==38);
                assert(!memcmp(m3map,m1bmap,sizeof m3map));
                for(unsigned x=0;x<38;x++){
                    uint16_t expected=R46_P4_TileAt(bank,x,row);
                    assert(m3map[x]==expected);
                    assert(R46_M3_TileAt(packed,1672,bank,x,row)==expected);
                    uint32_t tile1[8],tile2[8];
                    for(unsigned i=0;i<8;i++)tile1[i]=tile2[i]=0xa5a5a5a5u;
                    uint16_t old=R46_P4_PackIfDynamic(bank,x,row,tile1);
                    uint16_t now=R46_M3_PackDynamic(packed,1672,bank,x,row,tile2);
                    assert(now==old);
                    assert(!memcmp(tile1,tile2,sizeof tile1));
                    if(now){
                        uint32_t owned[8]={0};
                        assert(R46_M3_PackOwned(&owner,packed,1672,
                            bank,x,row,owned)==now);
                        assert(!memcmp(owned,tile1,sizeof owned));
                    }
                }
            }
        }
        assert(!memcmp(snapshot,packed,sizeof snapshot));
    }
    assert(R46_M3_Request(&owner,R46_M3_CELL));
    assert(!R46_M3_MayWrite(&owner,R46_M3_PIXEL4));
    assert(R46_M3_AckQuiesce(&owner,R46_M3_QUIESCE_ALL));
    assert(R46_M3_AckReconfigure(&owner,R46_M3_RECONFIG_ALL));
    assert(R46_M3_Commit(&owner));
    assert(R46_M3_MayWrite(&owner,R46_M3_CELL));
    assert(!R46_M3_MayWrite(&owner,R46_M3_PIXEL4));
    assert(owner.epoch==3);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-m3a-') as d:
    src=Path(d)/'test.c';exe=Path(d)/'test';src.write_text(test)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-DDOOM_R46_M1','-DDOOM_R46_M1B','-DDOOM_R46_M2B',
        '-DDOOM_R46_M2C','-DDOOM_R20_REG_COLUMNS',
        '-I'+str(root/'src'),
        str(root/'src/r46_m3_owner.c'),str(root/'src/r46_m3_tiles.c'),
        str(root/'src/r46_pixel4_vram.c'),str(src),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M3A PASS: 28 frames x 2 banks x 798 tiles, bit-exact M1B patterns and 8x8/4x4 handoff gate')
