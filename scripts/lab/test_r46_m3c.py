#!/usr/bin/env python3
"""M3C: host C test for four native 4x4 frames and guarded bank staging.

Hardware video behavior is source audited and must be visually checked
by the user in BlastEm; host tests cannot establish DMA/VBlank timing.
"""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
video=(root/'src/r46_m3c_video.c').read_text()
required=(
    'VDP_setBGAAddress(0xE000u);',
    'VDP_setBGAAddress(0xC000u);',
    'VDP_getBGAAddress()==0xC000u',
    'VDP_setEnable(FALSE);','VDP_setEnable(TRUE);',
    'R20_StopVideo();','R20_AbortVideo();',
    'VDP_waitDMACompletion();',
    'R46_M3_AckQuiesce','R46_M3_AckReconfigure',
    'R46_M3_MayWrite','R46_M3_Commit',
    'R46_M3C_StageBank','R46_M3C_BankWritable',
    'R46_M3C_MakePattern','R46_M3_PackOwned',
    'R46_M3C_TilesUploaded','R46_M3C_MapRowWritten',
    'R46_M3C_CommitBank(stage,1)',
    'VDP_setTileMapDataRect','SYS_doVBlankProcess();',
    'reload_cell_tiles();','restore_cell_palette();'
)
for token in required: assert token in video,token
assert 'for(uint16_t phase=0;phase<4;phase++)' in video
assert 'for(uint16_t frame=0;frame<45;frame++)' in video
assert video.index('VDP_setBGAAddress(0xE000u);')<video.index('m3c_upload_hidden_bank(&owner')
assert video.index('VDP_setBGAAddress(0xC000u);')<video.index('reload_cell_tiles();')
assert 'static uint8_t ' not in video and 'MEM_alloc' not in video
assert '0xC000' in video and '0xD400' in video and '0xE000' in video
assert 'VDP_setEnable(FALSE);' in video[video.index('static void m3c_swap_map_while_blanked'):video.index('R46_M3C_MapRowWritten')]
assert 'VDP_setEnable(TRUE);' in video[video.index('R46_M3C_CommitBank(stage,1)'):video.index('__attribute__((noinline))')]
source=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "r46_m3c_bank.h"
#include "r46_m3c_pattern.h"
#include "r46_m3_tiles.h"
#include "r46_pixel4_raster.h"
uint16_t _s_screen[38*28];
int main(void){
    assert(R46_M3C_BankValidate()&&R46_M3C_PatternValidate());
    r46_m3c_bank_t b;
    R46_M3C_BankInit(&b);
    assert(b.visible_bank==R46_M3C_NO_BANK && b.commits==0);
    assert(!R46_M3C_CommitBank(&b,1));
    assert(!R46_M3C_StageBank(&b,2));
    assert(R46_M3C_StageBank(&b,0));
    assert(!R46_M3C_StageBank(&b,1));
    assert(R46_M3C_BankWritable(&b,0));
    assert(!R46_M3C_BankWritable(&b,1));
    assert(!R46_M3C_TilesUploaded(&b,799));
    assert(!R46_M3C_MapRowWritten(&b,1));
    assert(!R46_M3C_TilesUploaded(&b,0));
    assert(R46_M3C_TilesUploaded(&b,798));
    assert(!R46_M3C_CommitBank(&b,1));
    assert(!R46_M3C_MapRowWritten(&b,0));
    assert(!R46_M3C_MapRowWritten(&b,22));
    assert(R46_M3C_MapRowWritten(&b,1));
    assert(!R46_M3C_BankWritable(&b,0));
    assert(!R46_M3C_MapRowWritten(&b,1));
    assert(!R46_M3C_TilesUploaded(&b,1));
    for(int y=2;y<=21;y++)assert(R46_M3C_MapRowWritten(&b,y));
    assert(!R46_M3C_CommitBank(&b,0));
    assert(R46_M3C_CommitBank(&b,1));
    assert(b.visible_bank==0 && b.pending_bank==R46_M3C_NO_BANK);
    assert(!R46_M3C_StageBank(&b,0));

    /* Begin independent 4-phase run, 0->1->0->1, exactly 798 tiles. */
    R46_M3C_BankInit(&b);
    r46_m3_owner_t o; R46_M3_OwnerInit(&o);
    assert(R46_M3_Request(&o,R46_M3_PIXEL4));
    assert(R46_M3_AckQuiesce(&o,R46_M3_QUIESCE_ALL));
    assert(R46_M3_AckReconfigure(&o,R46_M3_RECONFIG_ALL));
    assert(R46_M3_Commit(&o));
    uint8_t mem[1674],*pixels=mem+1;
    uint8_t first=255;
    for(int phase=0;phase<4;phase++){
        unsigned bank=(unsigned)phase&1u;
        memset(mem,0xa5,sizeof mem);
        assert(R46_M3C_StageBank(&b,bank));
        assert(R46_M3C_BankWritable(&b,bank));
        assert(!R46_M3C_MakePattern(pixels,1671,phase));
        assert(mem[1]==0xa5);
        assert(!R46_M3C_MakePattern(pixels,1672,4));
        assert(R46_M3C_MakePattern(pixels,1672,phase));
        assert(mem[0]==0xa5 && mem[1673]==0xa5);
        for(unsigned i=0;i<76;i++)assert(pixels[i]==0);
        uint8_t sample=R46_P4_ReadSample(pixels,1672,0,3);
        if(phase)assert(sample!=first);
        first=sample;
        for(unsigned y=1;y<=21;y++){
            uint16_t row[38];
            assert(R46_M3_MapRow(pixels,1672,bank,y,row)==38);
            for(unsigned x=0;x<38;x++){
                uint32_t tile[8]={0};
                uint16_t index=R46_M3_PackOwned(&o,pixels,1672,bank,x,y,tile);
                assert(index==row[x]);
                if(bank==0)assert(index>=54&&index<=851);
                else assert(index>=890&&index<=1687);
                for(unsigned k=0;k<8;k++)
                    assert(((tile[k]>>28)^((tile[k]>>12)&15u))==1u);
            }
            assert(R46_M3C_TilesUploaded(&b,38));
        }
        assert(b.uploaded==798 && !R46_M3C_TilesUploaded(&b,1));
        for(unsigned y=1;y<=21;y++)assert(R46_M3C_MapRowWritten(&b,y));
        assert(!R46_M3C_CommitBank(&b,0));
        assert(R46_M3C_CommitBank(&b,1));
        assert(b.visible_bank==bank && b.commits==(unsigned)phase+1);
    }
    /* BG_A must be relocated because 890..1687 crosses C000.
     * E000..EFFF must remain clear of both banks and font patterns. */
    assert(54u*32u<0xC000u);
    assert(1688u*32u>0xC000u);
    assert(1688u*32u<=0xD400u);
    assert(0xE000u>1688u*32u);
    assert(!R46_M3C_StageBank(&b,1));
    assert(R46_M3C_StageBank(&b,0));
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='r46-m3c-') as d:
    main=Path(d)/'main.c';exe=Path(d)/'test'
    main.write_text(source)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-DDOOM_R46_M1','-DDOOM_R46_M1B',
        '-DDOOM_R46_M2B','-DDOOM_R46_M2C',
        '-DDOOM_R20_REG_COLUMNS',
        '-I'+str(root/'src'),
        str(root/'src/r46_pixel4_raster.c'),
        str(root/'src/r46_m3c_bank.c'),
        str(root/'src/r46_m3c_pattern.c'),
        str(root/'src/r46_m3_owner.c'),
        str(root/'src/r46_m3_tiles.c'),
        str(main),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('R46 M3C PASS: 4 phases x 798 native tiles, guarded hidden-bank write and VBlank stage protocol')
