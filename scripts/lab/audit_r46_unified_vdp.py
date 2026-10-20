#!/usr/bin/env python3
"""R46 M1B: evaluate unified-VRAM plan from October optimisation review.

This is a static feasibility audit, NOT an enablement of VDP registers.
Both renderers cannot keep their tiles simultaneously in the overlapping
tile range; M3 must drain VBlank DMA, swap patterns and restore palettes.
"""
from pathlib import Path
import json
import re
import argparse

root=Path(__file__).resolve().parents[2]
cell=(root/'src/i_genesisv.c').read_text()
pixel=(root/'src/r22_video.inc').read_text()
vram=(root/'src/r46_pixel4_vram.c').read_text()
secondary=(root/'src/r46_pixel4_secondary.c').read_text()
model=(root/'src/r46_pixel4_vram.h').read_text()
wi=(root/'src/wi_libt.c').read_text()

# Grounded in existing source, not assumptions about unexpanded SDK macros.
assert '#define SOLID_TILE_INDEX  TILE_USER_INDEX' in cell
assert 'VDP_setPlaneSize(64, 32, TRUE)' in cell
assert 'VDP_setWindowAddress(0xF000)' in pixel
assert 'VDP_setBGBAddress(0xE000)' in pixel
assert 'VDP_setSpriteListAddress(0xFC00)' in pixel
assert 'VDP_setHScrollTableAddress(0xFC00)' in pixel
assert 'TILE_FONT_INDEX!=1696' in pixel
assert 'VDP_setPlaneSize(64,32,FALSE)' in pixel
assert 'R46_P4_PackIfDynamic' in vram
assert '#define WI_TEXT_WIDTH 38' in wi
assert '#define WI_TEXT_HEIGHT 22' in wi
assert '_s_screen[38 * 28]' in secondary

r39f=16+105+105
proposed_base=16
cell_first,cell_last=proposed_base,proposed_base+r39f-1
bank0_first,bank0_last=54,851
bank1_first,bank1_last=890,1687
font_first=1696
dynamic_patterns=38*21
assert r39f==226 and cell_last==241
assert bank0_last-bank0_first+1==798
assert bank1_last-bank1_first+1==798
assert font_first-bank1_last-1==8
assert cell_first<=bank0_first<=cell_last
assert not (cell_first<=bank1_first<=cell_last)
assert 16+836+38+798-1==bank1_last
assert 38*28*2==2128 and 38*44==1672

report={
    'type':'R46 M1B design feasibility, not VDP configuration',
    'cell_tiles':{'count':r39f,'proposed_base':proposed_base,
                  'first':cell_first,'last':cell_last,
                  'base_currently_sdk_macro':'TILE_USER_INDEX',
                  'existing_primary_is_not_yet_relocated':True},
    'pixel4_tiles':{'solid_range':[0,15],
                    'bank0_dynamic':[bank0_first,bank0_last],
                    'bank1_dynamic':[bank1_first,bank1_last],
                    'font_first':font_first,'free_tiles_before_font':8},
    'overlap':{'cells_vs_bank0':[bank0_first,cell_last],
               'simultaneous_patterns_safe':False,
               'requires_reupload_on_every_mode_transition':True},
    'shared_wram':{'tilemap_8x8_bytes':2128,'pixel4_frame_bytes':1672,
                   'extra_native_tilemap_allocated_bytes':0,
                   'per_row_map_scratch_bytes':76},
    'existing_vdp_setup':{'cell':'64x32 planes, uses SGDK tile macro; verify actual primary registers at runtime',
                          'pixel4':'BGA/BGB=E000, Window=F000, SAT/HScroll=FC00, Font=1696'},
    'safe_steps':[
        'M2: geometry, clip and projection by active mode, do not duplicate WRAM buffers',
        'M3: drain queued R20 DMA / any Z80 bus arbitration before changing VRAM',
        'M3: configure shared plane/window layout; re-upload cell tiles or pixel4 dynamic patterns when switching',
        'M3: restore the four CRAM palettes and 320x224 native WINDOW text after every transition',
        'M4: expose runtime renderer toggle only after state and gameplay stability tests'
    ],
    'not_implemented':['unified VDP registers','runtime upload','ISR handoff','runtime geometry dispatch','Options toggle']
}
parser=argparse.ArgumentParser()
parser.add_argument('--out',type=Path)
args=parser.parse_args()
out=json.dumps(report,indent=2,ensure_ascii=False)+'\n'
if args.out:
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(out,encoding='utf-8')
print(out)
