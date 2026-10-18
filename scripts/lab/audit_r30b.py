#!/usr/bin/env python3
"""Compare R30b audio-identical native control and two adaptive Bayer modes.

Compilation and byte counts are NOT evidence of accurate visuals or sound;
the user will test BlastEm and original Mega Drive separately.
"""
import hashlib,json,sys
from pathlib import Path
dist=Path(sys.argv[1]);names=sys.argv[2:]
expected={
    'control-play':'none',
    'bayer4-play':'bayer4',
    'bayer4-perf':'bayer4',
    'bayer8-play':'bayer8',
    'bayer8-perf':'bayer8',
}
data=[];inputs=[]
for name in names:
    assert name in expected,name
    rom=dist/('doom-md-r30b-'+name+'.bin')
    elf=rom.with_suffix('.elf')
    assert rom.is_file() and elf.is_file(),name
    code=rom.read_bytes()
    opts=(dist/('flags-doom-md-r30b-'+name+'.txt')).read_text()
    required=('-DDOOM_R30_NATIVE','-DDOOM_R25_MUSIC',
              '-DDOOM_R29_XGM2','-DDOOM_R29_MULTI',
              '-DDOOM_R27_GROUP_SIDE','-DDOOM_R27_GROUP_LINE')
    assert all(r in opts for r in required),name
    assert '-DSFX_SILENT' in opts,name
    if name.endswith('-perf'):
        assert '-DTIMEDEMO' in opts,name
    else:
        assert '-DTIMEDEMO' not in opts,name
    report=json.loads((dist/('art-'+name+'.json')).read_text())
    assert report['adaptive_dither']==expected[name],name
    assert [s['key'] for s in report['screens']]==['title','inter','final']
    for s in report['screens']:
        assert s['adaptive_dither']==expected[name]
        assert s['tiles']<=1120,name
        if expected[name]!='none':
            assert s['candidate_pixels']>0, (name,s['key'])
            assert s['changed_pixels']>0, (name,s['key'])
        else:
            assert s['changed_pixels']==0 and s['candidate_pixels']==0
    inputs.append((name,report))
    data.append(dict(name=name,mode=expected[name],
                     rom_bytes=len(code),fits_2mib=len(code)<=2097152,
                     sha256=hashlib.sha256(code).hexdigest(),
                     artwork_total_bytes=sum(
                       s['packed_bytes']+s['map_bytes']+s['palette_bytes']
                       for s in report['screens']),
                     adaptive_changed_pixels=sum(s['changed_pixels'] for s in report['screens']),
                     status='COMPILED_NOT_EMULATOR_TESTED'))
for _,rep in inputs[1:]:
    assert rep['source_wad_sha256']==inputs[0][1]['source_wad_sha256']
    for base,screen in zip(inputs[0][1]['screens'],rep['screens']):
        assert base['source_sha256']==screen['source_sha256']
for obj in data:
    print(f"{obj['name']}: {obj['rom_bytes']} ROM bytes; graphics {obj['artwork_total_bytes']} bytes; changed {obj['adaptive_changed_pixels']}; <=2MiB? {obj['fits_2mib']}")
(dist/'R30B-AUDIT.json').write_text(json.dumps(
    dict(matched_source=True,variants=data),indent=2)+'\n')
