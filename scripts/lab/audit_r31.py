#!/usr/bin/env python3
"""R31 experimental ROM/PCM/WAD footprint audit: no runtime safety claim."""
from pathlib import Path
import hashlib,json,sys
dist=Path(sys.argv[1])
modes={'ctl-play':'silent','h6-play':'half','h6-perf':'half',
       'mix-play':'mixed','mix-perf':'mixed','h13-play':'full'}
names=sys.argv[2:] if len(sys.argv)>2 else list(modes)
items=[]
for name in names:
    assert name in modes
    stem='doom-md-r31-'+name
    binpath=dist/(stem+'.bin')
    elfpath=dist/(stem+'.elf')
    assert binpath.is_file() and elfpath.is_file(),name
    rom=binpath.read_bytes()
    flags=(dist/('flags-'+stem+'.txt')).read_text()
    required=('-DDOOM_R30_NATIVE','-DDOOM_R25_MUSIC','-DDOOM_R29_XGM2',
              '-DDOOM_R29_MULTI','-DDOOM_R27_GROUP_SIDE','-DDOOM_R27_GROUP_LINE')
    assert all(s in flags for s in required),name
    if name.endswith('-perf'):
        assert '-DTIMEDEMO' in flags,name
    else:assert '-DTIMEDEMO' not in flags,name
    assert ('-DSFX_SILENT' in flags)==(modes[name]=='silent'),name
    assert ('-DDOOM_R31_SFX' in flags)==(modes[name]!='silent'),name
    pic=json.loads((dist/('art-'+name+'.json')).read_text())
    assert pic['adaptive_dither']=='bayer8',name
    sound=json.loads((dist/('sfx-'+name+'.json')).read_text())
    assert sound['mode']==modes[name],name
    if modes[name]=='silent':
        assert sound['count']==0 and sound['sum_pcm_bytes']==0
    else:
        assert sound['count']>=40 and sound['sum_pcm_bytes']>0
        assert sound['source_sha256'] is not None
        assert all(s['rate'] in (6650,13300) for s in sound['samples'])
        if modes[name]=='half':
            assert sound['pcm_rates']=={'6650':sound['count']}
        if modes[name]=='full':
            assert sound['pcm_rates']=={'13300':sound['count']}
    rawpath=dist/('payload-'+name+'.txt')
    payload_bytes=int(rawpath.read_text().strip()) if rawpath.exists() else None
    data={'name':name,'mode':modes[name],'rom_bytes':len(rom),
          'payload_bytes_before_padding':payload_bytes,
          'payload_required_savings_to_2mib':max(0,payload_bytes-2097152) if payload_bytes is not None else None,
          'rom_fits_2mib':len(rom)<=2097152,'pcm_bytes':sound['sum_pcm_bytes'],
          'pcm_count':sound['count'],'sample_rates':sound['pcm_rates'],
          'source_wad_hash':sound['source_sha256'],
          'sha256':hashlib.sha256(rom).hexdigest(),
          'status':'COMPILED_UNTESTED_AUDIO'}
    items.append(data)
    print(name,data['rom_bytes'],'bytes; raw',payload_bytes,
          'SFX',data['pcm_bytes'],'samples',data['pcm_count'],
          'fits 2MiB',data['rom_fits_2mib'])
sourcehashes={x['source_wad_hash'] for x in items if x['source_wad_hash']}
assert len(sourcehashes)<=1,'All SFX versions must use same source WAD'
(dist/'R31-AUDIT.json').write_text(json.dumps(items,indent=2)+'\n')
