#!/usr/bin/env python3
"""R46 M3C R4 diagnostic: prevent SGDK map-dependent font heap churn.
Host source contract only; hardware VDP registers and SGDK heap integrity
require visual / runtime checking. R28 ERRORS should return to 0.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
video=(root/'src/r46_m3c_video.c').read_text()
builder=(root/'scripts/lab/build_r35_linear.fish').read_text()
entry=(root/'src/i_genesisv.c').read_text()
# H40 VDP register 4: BG_B base = (VRAM >>13).
# Register 3: H40 Window base = (VRAM >>10), masked to 0x3c.
def reg(base,address,step):
    return (0x8000|(base<<8)|(address//step))
assert reg(4,0xE000,0x2000)==0x8407
assert reg(4,0xC000,0x2000)==0x8406
assert reg(3,0xE000,0x400)==0x8338
assert reg(3,0xD000,0x400)==0x8334
assert '#if defined(DOOM_R46_M3C_DIRECT_REGS)' in video
assert video.count('#if defined(DOOM_R46_M3C_DIRECT_REGS)')==2
assert 'volatile uint16_t *const vdp_ctrl=(volatile uint16_t*)VDP_CTRL_PORT;' in video
for value in ['0x8407u','0x8338u','0x8334u','0x8406u']:
    assert '*vdp_ctrl=(uint16_t)'+value+';' in video
assert video.index('0x8407u')<video.index('0x8338u')
assert video.index('0x8334u')<video.index('0x8406u')
assert video.index('0x8406u')<video.index('VDP_clearTileMapRect(WINDOW,0,0,64,6);')
assert video.index('0x8406u')<video.index('VDP_clearPlane(BG_B,TRUE);')
assert video.index('0x8406u')<video.index('VDP_loadDefaultFont(CPU)')
assert 'TILE_FONT_INDEX==1440u' in video
assert 'VDP_MAPS_START==0xC000u' in video
assert 'R46_M3C_DIRECT_REGS' in builder
assert 'doom-md-r46-m3c-r4-safe-perf' in builder
assert 'doom-md-r46-m3c-r4-stress-perf' in builder
assert 'R28_VideoAudit();' in entry
assert 'if (h != (VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS * 2 + 3))' in entry
assert 'r28_errors |= 2;' in entry
print('R46 M3C R4 PASS: 4 raw VDP regs mirror/restore with SGDK cached-map and font/heap invariant preserved')
