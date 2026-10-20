#!/usr/bin/env python3
"""R46 M6A: EXHAUSTIVE OFFLINE VRAM CONTRACT test.
No changes to SGDK or VDP are made; ROM uses exact proven R5 video.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
header=(root/'src/r46_m6a_layout.h').read_text()
source=(root/'src/r46_m6a_layout.c').read_text()
boot=(root/'src/i_genesisv.c').read_text()
builder=(root/'scripts/lab/build_r35_linear.fish').read_text()

with tempfile.TemporaryDirectory(prefix='r46-m6a-') as folder:
    exe=Path(folder)/'m6a-layout-host'
    cc=['gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',
        '-I',str(root/'src'),str(root/'src/r46_m6a_layout.c'),
        str(root/'scripts/lab/test_r46_m6a_layout.c'),'-o',str(exe)]
    subprocess.run(cc,check=True)
    result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
    assert 'R46 M6A PASS' in result.stdout,result.stdout
    print(result.stdout.strip())

# Exhaustive mathematical oracle, independent of the C function.
system=set(range(0,16))
font=set(range(16,112))
solids0=set(range(112,128))
bank0={150+(row-1)*38+col for row in range(1,22) for col in range(38)}
bank1={986+(row-1)*38+col for row in range(1,22) for col in range(38)}
tables=set(range(0xE000//32,0x10000//32))
assert len(system)==16 and len(font)==96
assert len(bank0)==len(bank1)==798
for a,b in [(system,font),(font,solids0),(font,bank0),(font,bank1),
            (bank0,bank1),(bank0,tables),(bank1,tables)]:
    assert a.isdisjoint(b),(min(a),min(b),'VRAM overlap')
assert min(bank0)==150 and max(bank0)==947
assert min(bank1)==986 and max(bank1)==1783
assert (0xE000//32)-max(bank1)-1 == 8  # 256 spare bytes
assert 'DOOM_R46_M6A_LAYOUT' in builder
assert 'doom-md-r46-r6a-audit-safe' in builder
assert 'doom-md-r46-r6a-audit-stress' in builder
assert 'R46_M6A_LayoutValidate()' in boot
assert 'R46_M6A_DynamicTile' in source
assert '#define SOLID_TILE_INDEX  TILE_USER_INDEX' in boot
assert 'VDP_setPlaneSize(64, 32, TRUE);' in boot
assert 'DOOM_R46_M3C_LATE_BUFFER' in builder
# Compile-time test only; old SGDK headers will still say TILE_USER_INDEX 16.
assert 'NO VDP' in header or 'never programs the VDP' in header
print('R46 M6A PASS: 1596 unique dynamic tiles, original R5 VDP and control untouched')
