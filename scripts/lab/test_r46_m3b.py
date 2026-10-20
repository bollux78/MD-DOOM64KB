#!/usr/bin/env python3
"""M3B: compile the real synthetic frame generator and VRAM packer on host.
Also audit the isolated hardware path for required ownership and restore
barriers. This does not pretend to emulate Genesis hardware or DMA timing.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
video=(root/'src/r46_m3b_video.c').read_text()
required=('R20_StopVideo();','VDP_waitDMACompletion();',
          'R20_AbortVideo();','R46_M3_AckQuiesce',
          'R46_M3_AckReconfigure','R46_M3_Commit',
          'R46_M3_MayWrite','R46_M3B_MakePattern',
          'R46_M3_PackOwned','VDP_loadTileData',
          'VDP_setTileMapDataRect','reload_cell_tiles();',
          'restore_cell_palette();','SYS_doVBlankProcess()')
for token in required:
    assert token in video,token
assert 'static uint8_t ' not in video and 'MEM_alloc' not in video
assert 'for(uint16_t i=0;i<120;i++)' in video
assert 'for(uint16_t y=1;y<=21;y++)' in video
assert 'for(uint16_t x=0;x<38;x++)' in video
pattern=(root/'src/r46_m3b_pattern.c').read_text()
assert 'R22_Put(pixels,x,y,c)' in pattern
source=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "r46_m3b_pattern.h"
#include "r46_m3_tiles.h"
#include "r46_pixel4_vram.h"
uint16_t _s_screen[38*28];
int main(void){
    assert(R46_M3B_PatternValidate());
    r46_m3_owner_t o;
    R46_M3_OwnerInit(&o);
    uint8_t mem[1674];
    memset(mem,0xa5,sizeof mem);
    uint8_t *pixels=mem+1;
    assert(!R46_M3B_MakePattern(pixels,1671));
    assert(mem[0]==0xa5 && mem[1]==0xa5 && mem[1673]==0xa5);
    assert(R46_M3B_MakePattern(pixels,1672));
    assert(mem[0]==0xa5 && mem[1673]==0xa5);
    for(unsigned i=0;i<76;i++)assert(pixels[i]==0);
    uint32_t tile[8];
    assert(!R46_M3_PackOwned(&o,pixels,1672,0,0,1,tile));
    assert(R46_M3_Request(&o,R46_M3_PIXEL4));
    assert(R46_M3_AckQuiesce(&o,R46_M3_QUIESCE_ALL));
    assert(R46_M3_AckReconfigure(&o,R46_M3_RECONFIG_ALL));
    assert(R46_M3_Commit(&o));
    uint32_t tiles=0;
    for(unsigned bank=0;bank<2;bank++){
        for(unsigned y=1;y<=21;y++){
            uint16_t map[38];
            assert(R46_M3_MapRow(pixels,1672,bank,y,map)==38);
            for(unsigned x=0;x<38;x++){
                uint16_t index=R46_M3_TileAt(pixels,1672,bank,x,y);
                assert(index>=54 && index<=1687);
                assert(map[x]==index);
                uint32_t packed[8]={0};
                assert(R46_M3_PackOwned(&o,pixels,1672,bank,x,y,packed)==index);
                for(unsigned i=0;i<8;i++){
                    unsigned p0=packed[i]>>28;
                    unsigned p1=(packed[i]>>12)&15u;
                    assert((p0^p1)==1u);
                }
                tiles++;
            }
        }
    }
    assert(tiles==1596);
    assert(mem[0]==0xa5 && mem[1673]==0xa5);
    assert(R46_M3_Request(&o,R46_M3_CELL));
    assert(!R46_M3_PackOwned(&o,pixels,1672,0,0,1,tile));
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-m3b-') as d:
    path=Path(d)/'test.c';exe=Path(d)/'test';path.write_text(source)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-DDOOM_R46_M1','-DDOOM_R46_M1B','-DDOOM_R46_M2B',
        '-DDOOM_R46_M2C','-DDOOM_R20_REG_COLUMNS',
        '-I'+str(root/'src'),str(root/'src/r46_pixel4_raster.c'),
        str(root/'src/r46_m3b_pattern.c'),
        str(root/'src/r46_m3_tiles.c'),
        str(root/'src/r46_m3_owner.c'),
        str(path),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M3B PASS: all 1596 tiles dynamic, reserved topbar and guards, owner-gated access')
