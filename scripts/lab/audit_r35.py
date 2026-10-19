#!/usr/bin/env python3
"""Reject accidental codec, non-Bayer8 art, >4MiB, missing soundtrack or invalid variants."""
from pathlib import Path
import hashlib, json, sys, struct
p=Path(sys.argv[1]);names=sys.argv[2:]
expect={'cell-play','cell-perf'}
assert set(names)==expect,(names,expect)
out=[]
art_sources=[]
for variant in names:
    name='doom-md-r37-'+variant
    rom=p/(name+'.bin')
    data=rom.read_bytes()
    assert len(data)<=4*1024*1024 and len(data)%0x20000==0,(name,len(data))
    assert data[0x100:0x110]==b'SEGA MEGA DRIVE ',name
    assert struct.unpack_from('>II',data,0x1A0)==(0,len(data)-1),name
    flags=(p/('flags-'+name+'.txt')).read_text()
    is_cell=variant.startswith('cell')
    assert '-DDOOM_R35D_CHECKER' in flags,(name,'checker flag required')
    assert ('-DDOOM_R37_BSP_PROFILE' in flags)==variant.endswith('play'),(name,'live counters only in play')
    assert ('-DDOOM_R20_COUNTERS' not in flags and '-DDOOM_ROUTINE_PROFILE' not in flags),name
    if is_cell:
        detail=json.loads((p/('dither-'+variant+'.json')).read_text())
        assert detail['mode']=='r35d-checker-strong',detail
        assert detail['checker_colors']>=140,(name,detail['checker_colors'])
        assert detail['checker_colormap_cells']>=4500,(name,detail['checker_colormap_cells'])
        assert detail['unique_checker_tiles']>=60,(name,detail['unique_checker_tiles'])
        assert detail['checker_tile_max']==120,detail
    else:
        assert not (p/('dither-'+variant+'.json')).exists(),name
    assert '-DDOOM_R35_ART_RAW' in flags,name
    assert '-DDOOM_R30_NATIVE' in flags,name
    assert '-DDOOM_R29_XGM2' in flags,name
    assert '-DDOOM_R29_MULTI' in flags,name
    assert '-DDOOM_R31_SFX' in flags,name
    assert '-DDOOM_R25_MUSIC' in flags,name
    assert ('-DDOOM_R22_PIXEL4' in flags)==variant.startswith('pixel4'),(name,flags)
    assert ('-DTIMEDEMO' in flags)==variant.endswith('perf'),(name,flags)
    # Important: no R34 ADPCM, PackBits, or REJECT compression flags.
    assert '-DDOOM_R34_AUDIO' not in flags and '-DDOOM_R34_WAD' not in flags
    art=json.loads((p/('art-'+variant+'.json')).read_text())
    assert art['adaptive_dither']=='bayer8'
    assert art['storage']=='raw'
    assert len(art['screens'])==3
    for t in art['screens']:
        assert t['storage']=='raw' and t['packed_bytes']==t['tiles']*32,(name,t)
    art_sources.append([(t['source_sha256'],t['packed_bytes'],t['tiles'],t['changed_pixels']) for t in art['screens']])
    sfx=json.loads((p/('sfx-'+variant+'.json')).read_text())
    assert sfx['mode']=='mixed' and sfx['count']==52,(name,sfx.get('mode'),sfx.get('count'))
    raw=int((p/('payload-'+variant+'.txt')).read_text().strip())
    assert raw<=len(data) and len(data)-raw<0x20000,(name,raw)
    out.append(dict(name=name,renderer=('4x4' if variant.startswith('pixel4') else '8x8'),
                    timedemo=variant.endswith('perf'),rom_bytes=len(data),
                    checkerboard=is_cell,
                    checker_colors=detail['checker_colors'] if is_cell else 0,
                    checker_colormap_cells=detail['checker_colormap_cells'] if is_cell else 0,
                    elf_payload_bytes=raw,free_bytes=len(data)-raw,
                    pcm_count=52,pcm_bytes=sfx.get('sum_pcm_bytes'),
                    art_raw_bytes=sum(t['packed_bytes'] for t in art['screens']),
                    sha256=hashlib.sha256(data).hexdigest()))
assert all(x==art_sources[0] for x in art_sources),(art_sources,'Native Bayer8 screens not identical across ROMs')
(p/'R37-AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
for v in out: print(json.dumps(v))
print('R37 audit PASSED: 8x8 strong checker; playable live BSP profiler plus clean timedemo; trimmed ROM, raw Bayer8, 52 PCM SFX, XGM2')
