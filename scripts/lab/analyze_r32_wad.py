#!/usr/bin/env python3
"""R32 WAD study: ROM savings vs required resident 68000 memory.
Does not modify any runtime pointers, mmap, SRAM mapping, or rendered pixels.
"""
from pathlib import Path
import argparse,collections,hashlib,json,re,struct,zlib,lzma

MAP_LOTS=('THINGS','LINEDEFS','SIDEDEFS','SEGS','SSECTORS',
          'NODES','SECTORS','REJECT','BLOCKMAP')
# These are retained past loading by the current renderer, physics,
# collision, R24 ROM things and other gameplay code.
RESIDENT=set(MAP_LOTS)
MAP_INDEX=set(f'E1M{i}' for i in range(1,10))
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('wad',type=Path)
    parser.add_argument('--json',type=Path,required=True)
    args=parser.parse_args()
    wad=args.wad.read_bytes()
    assert wad[:4] in (b'IWAD',b'PWAD')
    count=struct.unpack_from('>H',wad,4)[0]
    directory=struct.unpack_from('>I',wad,8)[0]
    assert directory+count*16<=len(wad)
    entries=[]
    current=None
    for i in range(count):
        p=directory+i*16
        off,size=struct.unpack_from('>IH',wad,p)
        name=wad[p+8:p+16].split(b'\0')[0].decode('ascii','replace')
        assert off+size<=len(wad)
        if name in MAP_INDEX:current=name
        elif current and name not in MAP_LOTS:
            # Metadata that is physically appended after the maps is classified below.
            current=None
        is_map=(current is not None and name in MAP_LOTS)
        match=re.match(r'^S([1-9])(?:LINES|OFFS|SUBS|SOUND|RTHING|RMAP|COFF|CIDX|ROFF|RIDX)$',name)
        level=current if is_map else 'E1M'+match.group(1) if match else None
        group='active_map_geometry' if is_map else 'active_map_metadata' if match else 'shared_asset'
        data=wad[off:off+size]
        compressed=zlib.compress(data,9) if size else b''
        xz=lzma.compress(data,preset=6,format=lzma.FORMAT_XZ) if size else b''
        if size:
            assert zlib.decompress(compressed)==data
            assert lzma.decompress(xz)==data
        entries.append(dict(index=i,name=name,level=level,group=group,
                            offset=off,size=size,
                            compressed_zlib=len(compressed),
                            compressed_xz=len(xz),
                            zlib_saved=max(0,size-len(compressed)),
                            xz_saved=max(0,size-len(xz)),
                            addressable_during_game=bool(is_map or match)))
    unique={}
    for row in entries:
        if row['size']:
            key=(row['offset'],row['size'])
            unique.setdefault(key,[]).append(row)
    total_compressed=sum(min(r[0]['size'],r[0]['compressed_zlib']) for r in unique.values())
    total_size=sum(key[1] for key in unique)
    groups={}
    for name in ['active_map_geometry','active_map_metadata','shared_asset']:
        rows=[r for r in entries if r['group']==name]
        uniq={ (r['offset'],r['size']):r for r in rows if r['size']}
        groups[name]=dict(lumps=len(rows),unique_bytes=sum(x['size'] for x in uniq.values()),
                         unique_zlib_potential=sum(max(0,x['zlib_saved']) for x in uniq.values()))
    maps={}
    for number in range(1,10):
        name=f'E1M{number}'
        pieces=[r for r in entries if r['level']==name and r['size']]
        map_geom=[r for r in pieces if r['group']=='active_map_geometry']
        size=sum(r['size'] for r in map_geom)
        worst=max(map_geom,key=lambda x:x['size']) if map_geom else None
        maps[name]=dict(lumps=[dict(lump=r['name'],bytes=r['size'],zlib_saved=r['zlib_saved'])
                               for r in map_geom],
                        geometry_bytes=size,
                        extra_metadata_bytes=sum(r['size'] for r in pieces
                                                 if r['group']=='active_map_metadata'),
                        would_fit_entire_64KiB=size<=65536,
                        largest_lump=dict(name=worst['name'],bytes=worst['size']) if worst else None,
                        geometry_zlib_potential=sum(r['zlib_saved'] for r in map_geom))
    # Any savings from lossless stream codecs in these tables must be accompanied
    # by a persistent output buffer or a new scheme for direct indexed reads.
    report=dict(
        input_wad=str(args.wad),
        wad_bytes=len(wad),
        wad_sha256=hashlib.sha256(wad).hexdigest(),
        count=count,
        physical_unique_data_bytes=total_size,
        physical_unique_zlib_saved=total_size-total_compressed,
        per_category=groups,
        maps=maps,
        targets_to_save=dict(silent_control=100940,
                             SFX_6650_play=418380,
                             SFX_mixed_play=531020,
                             SFX_13300_play=729420),
        limitations=[
            'THEORETICAL zlib savings are offline entropy, not implemented 68000 compression.',
            'W_GetLumpByNum returns ROM pointers and several map structures stay live for entire level.',
            '64KiB work RAM is shared with Doom heap (about 45KiB) and engine state.',
            '32KiB effective odd-lane SRAM is already allocated to dynamic map structures.',
            'Any runtime codec must preserve random access to hot geometry without FPS regression.',
            'Whole-level decompression cannot be assumed feasible; each map size is measured below.'
        ])
    args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_text(json.dumps(report,indent=2)+'\n')
    print('R32 WAD',len(wad),'bytes',count,'lumps')
    print('Physical unique bytes',total_size,
          'theoretical zlib saved',total_size-total_compressed)
    for group,meta in groups.items():print(group,meta)
    for name,d in maps.items():
        print(name,'geometry',d['geometry_bytes'],'metadata',d['extra_metadata_bytes'],
              'zlib geometry potential',d['geometry_zlib_potential'],
              'fits all 64KiB RAM',d['would_fit_entire_64KiB'])
    print('R31 SFX 6.65k goal: save at least 418380 actual ROM bytes.')
if __name__=='__main__':
    main()
