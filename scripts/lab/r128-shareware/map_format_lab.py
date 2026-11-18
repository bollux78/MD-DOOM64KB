#!/usr/bin/env python3
"""E1M1 map-format laboratory. Run immediately before the compiler."""
from pathlib import Path
import os,struct,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from convert_r24_episode import read_wad,write_wad

import shutil
template=Path('maplab-template')
template.mkdir(exist_ok=True)
for original in ('src/i_genesis.c','src/r_defs.h','src/doomdata.h','src/r_draw.c','src/m_text.c','src/g_game.c','src/p_sight.c','src/p_setup.c','src/r23_mapmem.c','scripts/doom64.wad'):
    target=template/Path(original).name
    if target.exists():shutil.copy2(target,original)
    else:shutil.copy2(original,target)
requested=os.environ['R128_MAP_FORMAT']
assert requested in ('control','side8','seg32','chunkrom','chunk128')
mode='seg32' if requested.startswith('chunk') else requested
for generated in ('src/rchunk_state.c','src/rchunk_data.c','src/rchunk_data.h','src/rchunk_state.h'):
    Path(generated).unlink(missing_ok=True)
path=Path('scripts/doom64.wad')
lumps=read_wad(path.read_bytes(),True)
# Retain one playable map and its static metadata.
kept=[]
for i,(name,data) in enumerate(lumps):
    if len(name)==4 and name.startswith('E1M'):
        keep=name=='E1M1'
    if name in ('THINGS','LINEDEFS','SIDEDEFS','SEGS','SSECTORS','NODES','SECTORS','REJECT','BLOCKMAP'):
        kept.append((name,data if keep else b""))
    elif len(name)==4 and name.startswith('E1M'):
        kept.append((name,data if keep else b""))
    elif name.startswith('S') and len(name)>2 and name[1].isdigit() and name[2:].startswith(('L','S','R','C','T')):
        kept.append((name,data if name[1]=='1' else b''))
    else:kept.append((name,data))
lumps=kept
sides=next(data for name,data in lumps if name=='SIDEDEFS')
lines=next(data for name,data in lumps if name=='LINEDEFS')
segs=next(data for name,data in lumps if name=='SEGS')
side_rows=list(struct.iter_unpack('>hBbbbB',sides))
mutable=set()
for offset in range(0,len(lines),32):
    row=struct.unpack_from('>hhhhHhhHHhhhhhBbb',lines,offset)
    if row[13] or row[16]:
        mutable.update(index for index in row[7:9] if index!=65535)
# Static snapshots contain no RAM addresses. Mutable switch/scroller sides use
# the original SRAM access path. Sector heights always come from live state.
def record(index):
    x,y,top,bottom,mid,sector=side_rows[index]
    return struct.pack('>hbbbBBB',x,top,bottom,mid,0,index in mutable,y)
snapshot=b''.join(record(i) for i in range(len(side_rows)))
def edit(file,old,new):
    p=Path(file);s=p.read_text();assert s.count(old)==1,(file,old[:65],s.count(old));p.write_text(s.replace(old,new))
if mode!='control':
    if mode=='side8':
        rows=[list(struct.unpack('>hbbbBBB',snapshot[i:i+8])) for i in range(0,len(snapshot),8)]
        header='static const struct { int16_t x; int8_t top,bottom,mid; uint8_t pad,dynamic,row; } rmap_side8[]={\n'
        header+=',\n'.join('{'+','.join(map(str,row))+'}' for row in rows)+'\n};\n'
        Path('src/rmap_side8.h').write_text(header)
        edit('src/r_draw.c','#define R27_SIDE(p,f) ((p)->f)','#include "rmap_side8.h"\n#define R27_SIDE(p,f) ((p)->f)')
        selector='&rmap_side8[curline->sidenum]'
    else:
        edit('src/r_defs.h','    uint8_t backsectornum;\n} seg_t;', '''    uint8_t backsectornum;
    int16_t prepared_x;
    int8_t prepared_top,prepared_bottom,prepared_mid;
    uint8_t prepared_pad,prepared_dynamic,prepared_row;
    uint8_t prepared_reserved[6];
} seg_t;''')
        edit('src/r_defs.h','assertSegSize[sizeof(seg_t) == 18','assertSegSize[sizeof(seg_t) == 32')
        new=b''
        for offset in range(0,len(segs),18):
            row=segs[offset:offset+18]
            side=struct.unpack_from('>H',row,12)[0]
            new+=row+record(side)+bytes(6)
        assert len(new)==len(segs)//18*32
        lumps=[(name,new if name=='SEGS' else data) for name,data in lumps]
        selector='(const rmap_view_t*)&curline->prepared_x'
        edit('src/r_draw.c','#define R27_SIDE(p,f) ((p)->f)', '''typedef struct { int16_t x; int8_t top,bottom,mid; uint8_t pad,dynamic,row; } rmap_view_t;
#define R27_SIDE(p,f) ((p)->f)''')
    for pointer in ('sidedef','side'):
        old=f'''    R27_ReadBlock({pointer},offsetof(side_t,textureoffset),
        offsetof(side_t,midtexture)+sizeof(side_snapshot.midtexture)-offsetof(side_t,textureoffset),
        (uint8_t*)&side_snapshot+offsetof(side_t,textureoffset));'''
        new=f'''    const __typeof__(*({selector})) *prepared={selector};
    if(prepared->dynamic){{
{old}
    }}else{{
        side_snapshot.textureoffset=prepared->x;
        side_snapshot.toptexture=prepared->top;
        side_snapshot.bottomtexture=prepared->bottom;
        side_snapshot.midtexture=prepared->mid;
    }}'''
        edit('src/r_draw.c',old,new)
# Prevent leaving the one-map lab via progression or the selector.
edit('src/m_text.c','static const menu_t LevelDef={9,LevelMenu,','static const menu_t LevelDef={1,LevelMenu,')
edit('src/g_game.c','    _g_gamemap = _g_wminfo.next+1;', '    _g_gamemap = 1;')
# The next build restores these files before selecting another map format.
template=Path('maplab-template')
template.mkdir(exist_ok=True)
if requested.startswith('chunk'):
    from chunk_format import apply
    lumps,chunk_report=apply(lumps,requested,edit,mutable,side_rows)
path.write_bytes(write_wad(lumps))
report=dict(format=requested,maps=['E1M1'],sides=len(side_rows),segs=len(segs)//18,
            mutable_sides=len(mutable),snapshot_bytes=len(snapshot) if mode=='side8' else 0,
            seg_stride=32 if mode=='seg32' else 18,wad_bytes=path.stat().st_size)
if requested.startswith('chunk'):
    report.update(chunk_report)
Path('src/rmap_lab_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
