#!/usr/bin/env python3
"""M3C R3: verify SGDK's dynamic font atlas overlap and opt-in repair.
This is a source/contract test; only emulator and hardware can verify glyphs.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
video=(root/'src/r46_m3c_video.c').read_text()
builder=(root/'scripts/lab/build_r35_linear.fish').read_text()
entry=(root/'src/i_genesisv.c').read_text()
bank1_start=890*32
bank1_end=(1687+1)*32-1
font_tiles=96
font_start=(0xC000//32-font_tiles)*32
font_end=0xC000-1
assert (bank1_start,bank1_end)==(0x6F40,0xD2FF)
assert (font_start,font_end)==(0xB400,0xBFFF)
assert bank1_start<font_start<font_end<bank1_end
assert (0xD000//32-font_tiles)*32==0xC400
assert (0xE000//32-font_tiles)*32==0xD400
assert video.count('VDP_setBGBAddress(0xC000u);')==1
assert video.count('VDP_setWindowAddress(0xD000u);')==1
assert '#if defined(DOOM_R46_M3C_FONT_RESTORE)' in video
assert 'VDP_MAPS_START==0xC000u' in video
assert 'TILE_FONT_INDEX==1440u' in video
assert 'VDP_loadDefaultFont(CPU)' in video
assert video.index('VDP_setBGBAddress(0xC000u);')<video.index('VDP_loadDefaultFont(CPU)')
assert video.index('restore_cell_palette();')<video.index('VDP_loadDefaultFont(CPU)')
assert video.index('VDP_loadDefaultFont(CPU)')<video.index('VDP_setEnable(TRUE);',video.index('VDP_loadDefaultFont(CPU)'))
assert 'R46_M3C_RestorePaletteCPU' in entry
assert "set defs $defs '-DDOOM_R46_M3C_FONT_RESTORE'" in builder
assert 'doom-md-r46-m3c-r3-safe-perf' in builder
assert 'doom-md-r46-m3c-r3-stress-perf' in builder
print('R46 M3C R3 PASS: font atlas B400..BFFF lies inside bank1, guarded 96-glyph synchronous reload after maps restoration')
