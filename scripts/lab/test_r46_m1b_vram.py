#!/usr/bin/env python3
"""Native host oracle for the R46 M1B 4x4 VRAM map & 32-byte patterns.

Builds the REAL C implementation on the host, with an isolated _s_screen
buffer, and compares its output against the standalone R22 formulas.
No Genesis VDP is accessed; this only proves the bank/pixel conversion.
"""
import subprocess
import tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[2]
src=root/'src/r46_pixel4_vram.c'
text=src.read_text()
assert 'VDP_' not in text and 'PAL_' not in text
assert 'R46_P4_Frame' in text and 'R46_P4_PatternRows' in text
assert 'R46_P4_MapRow' in text and 'R22_TileIndex' in text

test=r'''
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "r46_pixel4_vram.h"
uint16_t _s_screen[38*28];
static uint32_t rng=0x134679abUL;
static uint32_t rnd(void){rng=rng*1664525u+1013904223u;return rng;}
static uint32_t baseline_row(uint8_t p){
    return ((uint32_t)(p>>4)*0x11110000UL)|((uint32_t)(p&15)*0x1111UL);
}
static uint16_t baseline_tile(uint8_t top,uint8_t bottom,
                              unsigned bank,unsigned x,unsigned row){
    unsigned dynamic=16+bank*836+38+(row-1)*38+x;
    return (top==bottom && (top>>4)==(top&15)) ? (uint16_t)(top&15) : dynamic;
}
int main(void){
    /* Metadata-only call before any renderer is granted ownership */
    assert(R46_P4_VramValidate());
    assert(R46_P4_TileAt(2,0,1)==0);
    assert(R46_P4_TileAt(0,38,1)==0);
    assert(R46_P4_TileAt(0,0,0)==0);
    assert(R46_P4_TileAt(0,0,22)==0);
    uint16_t map[38]; uint32_t pattern[8];
    assert(R46_P4_MapRow(0,0,map)==0);
    assert(R46_P4_MapRow(2,1,map)==0);
    assert(R46_P4_MapRow(0,1,0)==0);
    uint32_t untouched[8]={0xA55A5AA5UL};
    assert(R46_P4_PackIfDynamic(2,0,1,untouched)==0);
    assert(R46_P4_PackIfDynamic(0,38,1,untouched)==0);
    assert(R46_P4_PackIfDynamic(0,0,0,untouched)==0);
    assert(R46_P4_PackIfDynamic(0,0,1,0)==0);
    assert(untouched[0]==0xA55A5AA5UL);
    uint8_t *pixels=(uint8_t *)(void *)_s_screen;
    for(unsigned pass=0;pass<40;pass++){
        for(unsigned i=0;i<sizeof(_s_screen);i++)
            pixels[i]=(uint8_t)rnd();
        if(pass==1)memset(pixels,0x00,1672);
        if(pass==2)memset(pixels,0xFF,1672);
        if(pass==3)memset(pixels,0x22,1672);
        if(pass==4)memset(pixels,0xF0,1672);
        uint8_t copy[sizeof(_s_screen)];
        memcpy(copy,pixels,sizeof(copy));
        for(unsigned bank=0;bank<2;bank++){
            for(unsigned row=1;row<=21;row++){
                assert(R46_P4_MapRow(bank,row,map)==38);
                for(unsigned x=0;x<38;x++){
                    unsigned offset=2*row*38+x;
                    uint8_t top=pixels[offset],bottom=pixels[offset+38];
                    uint16_t index=baseline_tile(top,bottom,bank,x,row);
                    assert(map[x]==index);
                    assert(R46_P4_TileAt(bank,x,row)==index);
                    uint32_t packed[8];
                    for(unsigned y=0;y<8;y++)packed[y]=0xA55A5AA5UL;
                    uint16_t produced=R46_P4_PackIfDynamic(bank,x,row,packed);
                    assert(produced==(index>=16 ? index : 0));
                    if(index<16){
                        for(unsigned y=0;y<8;y++)assert(packed[y]==0xA55A5AA5UL);
                    }
                    R46_P4_PatternRows(x,row,pattern);
                    if(index>=16)
                        assert(!memcmp(packed,pattern,sizeof(packed)));
                    for(unsigned y=0;y<4;y++){
                        assert(pattern[y]==baseline_row(top));
                        assert(pattern[y+4]==baseline_row(bottom));
                    }
                }
            }
        }
        assert(!memcmp(copy,pixels,sizeof(copy)));
    }
    /* test is intentionally libc-agnostic under the SGDK include path */
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-m1b-') as tmp:
    d=Path(tmp)
    file=d/'test.c'
    exe=d/'run'
    file.write_text(test)
    command=['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
             '-DDOOM_R46_M1B','-DDOOM_R46_M1','-DDOOM_R20_REG_COLUMNS',
             '-I'+str(root/'src'),str(src),str(file),'-o',str(exe)]
    subprocess.run(command,check=True)
    subprocess.run([str(exe)],check=True)
    print("R46 M1B PASS: 40 frames, two banks, Q3 skip-solid pack, no buffer modifications")
