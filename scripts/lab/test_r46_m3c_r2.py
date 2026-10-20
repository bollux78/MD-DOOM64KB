#!/usr/bin/env python3
"""R46 M3C R2: VRAM boundary and SGDK restoration safety audit.
No emulator screenshot or actual IRQ fidelity is claimed.
"""
from pathlib import Path
s=(Path(__file__).resolve().parents[2]/'src/r46_m3c_video.c').read_text()
entry=(Path(__file__).resolve().parents[2]/'src/i_genesisv.c').read_text()
builder=(Path(__file__).resolve().parents[2]/'scripts/lab/build_r35_linear.fish').read_text()
pairs=[
    ('BG_A',0xE000,0xEFFF),
    ('BG_B',0xC000,0xCFFF),
    ('WINDOW',0xD000,0xDFFF),
    ('FONT',0xD400,0xDFFF),
    ('BANK0',54*32,852*32-1),
    ('BANK1',890*32,1688*32-1)
]
a={label:(start,end) for label,start,end in pairs}
assert a['BANK1']==(0x6F40,0xD2FF)
assert a['BANK0'][1]<a['BANK1'][0]
assert a['BG_A'][0]>a['BANK1'][1]
assert a['BG_B'][0]<=a['BANK1'][1]
assert a['WINDOW'][0]<=a['BANK1'][1]
assert a['FONT'][0]>a['BANK1'][1]
# A 6x64 tile map rectangle at 2 bytes each clears only D000..D2FF.
window_clear=(0xD000,0xD000+6*64*2-1)
assert window_clear==(0xD000,0xD2FF)
assert window_clear[1]<a['FONT'][0]
required=(
 'VDP_getBGAAddress()==0xE000u',
 'VDP_getBGBAddress()==0xC000u',
 'VDP_getWindowAddress()==0xD000u',
 'VDP_setBGBAddress(0xE000u);',
 'VDP_setWindowAddress(0xE000u);',
 'VDP_setWindowAddress(0xD000u);',
 'VDP_clearTileMapRect(WINDOW,0,0,64,6);',
 'VDP_setBGBAddress(0xC000u);',
 'VDP_clearPlane(BG_B,TRUE);',
 'VDP_waitDMACompletion();',
 'R46_M3C_CommitBank(stage,1)',
 'VDP_setEnable(FALSE);',
 'VDP_setEnable(TRUE);',
 '#if defined(DOOM_R46_M3C_SAFE_BLANK)',
 '#if defined(DOOM_R46_M3C_STRESS)',
 'const uint16_t phases=12;',
 'const uint16_t phases=4;',
 'R46_M3C_MakePattern(pixels,1672,(uint16_t)(phase&3u))'
)
for text in required:assert text in s,text
assert s.index('VDP_setWindowAddress(0xE000u);') < s.index('m3c_upload_hidden_bank(&owner')
assert s.index('VDP_setWindowAddress(0xD000u);') < s.index('reload_cell_tiles();')
assert s.index('VDP_setWindowAddress(0xD000u);') < s.index('VDP_clearTileMapRect(WINDOW,0,0,64,6);')
assert s.index('VDP_clearTileMapRect(WINDOW,0,0,64,6);') < s.index('reload_cell_tiles();')
assert s.index('VDP_setBGBAddress(0xC000u);') < s.index('reload_cell_tiles();')
assert 'VDP_clearPlane(WINDOW' not in s
assert 'VDP_setBGAAddress(' not in s
assert 'R46_M3C_ShowVideoTest(_s_screen,I_BuildSolidTiles,R46_M3C_RestorePaletteCPU)' in entry
assert 'PAL_setColors(0,genpal_cram[0],64,CPU);' in entry
assert "DOOM_R46_M3C_SAFE_BLANK" in builder
assert "DOOM_R46_M3C_STRESS" in builder
print('R46 M3C R2 PASS: Window/BG_B overlap protected; 0xD400 font preserved; safe/stress gates isolated')
