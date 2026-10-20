#!/usr/bin/env python3
"""R46 M3C R4B: verify regression-safe R3 code path and raw VDP mode.

The old R3 (no DIRECT_REGS) must keep EXACT original source statements
and order. The known-good R3 ROM's binary hash is also checked by CI.
This is not a substitute for a visual or physical VDP test.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
video=(root/'src/r46_m3c_video.c').read_text()
build=(root/'scripts/lab/build_r35_linear.fish').read_text()
assert video.count('#if defined(DOOM_R46_M3C_DIRECT_REGS)')==3
assert 'if(!ok)I_Error("R46 M3C: %s",message);' in video
assert 'VDP_setEnable(TRUE);' in video
assert 'I_Error("R46 M3C R4B: %s",message)' in video
# Separate preprocessor branches. Do not modify old R3 control sequence.
start=video.index('    VDP_clearPlane(BG_A,TRUE); /* Clear pixel4')
section=video[start:]
old='''#else
    VDP_setWindowAddress(0xD000u); /* Restore inactive H40 Window. */
    /* Clear only the 6 damaged 64-word Window rows at D000..D2FF.
     * DO NOT clear all 32 rows: D400..DFFF contains SGDK font. */
    VDP_clearTileMapRect(WINDOW,0,0,64,6);
    VDP_setBGBAddress(0xC000u); /* Restore original BG_B base. */
#endif'''
assert old in section
direct='''*vdp_ctrl=0x8334u;
    VDP_clearTileMapRect(WINDOW,0,0,64,6);
    *vdp_ctrl=0x8406u;'''
assert direct in section
assert section.index('*vdp_ctrl=0x8334u;')<section.index('*vdp_ctrl=0x8406u;')
assert video.count('0x8407u')==1
assert video.count('0x8338u')==1
assert 'VDP_MAPS_START==0xC000u && TILE_FONT_INDEX==1440u' in video
assert 'VDP_loadDefaultFont(CPU)' in video
assert 'DOOM_R46_M3C_DIRECT_REGS' in build
assert 'doom-md-r46-r4b-safe-perf' in build
assert 'doom-md-r46-r4b-stress-perf' in build
print('R46 M3C R4B PASS: original R3 restore sequence untouched; direct registers isolated')
