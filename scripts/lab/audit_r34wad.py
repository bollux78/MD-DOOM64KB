#!/usr/bin/env python3
"""R34-WAD: verify independent REJECT compression experiments, no audio change."""
import hashlib,json,sys
from pathlib import Path
d=Path(sys.argv[1]);names=sys.argv[2:]
valid={'ctl-play':None,'ctl-perf':None,
       'r128-play':128,'r128-perf':128,
       'r256-play':256,'r256-perf':256}
rows=[]
for name in names:
    assert name in valid
    stem='doom-md-r34w-'+name
    rom=d/(stem+'.bin')
    elf=d/(stem+'.elf')
    assert rom.exists() and elf.exists()
    opts=(d/('flags-'+stem+'.txt')).read_text()
    flags=['-DDOOM_R30_NATIVE','-DDOOM_R29_XGM2','-DDOOM_R29_MULTI',
           '-DDOOM_R27_GROUP_SIDE','-DDOOM_R27_GROUP_LINE',
           '-DDOOM_R31_SFX','-DDOOM_R25_MUSIC']
    assert all(q in opts for q in flags),name
    assert '-DSFX_SILENT' not in opts,name
    assert ('-DTIMEDEMO' in opts)==name.endswith('perf'),name
    assert ('-DDOOM_R34_WAD_REJECT' in opts)==(valid[name] is not None),name
    assert ('-DDOOM_R34_REJECT_128' in opts)==(valid[name]==128),name
    audio=json.loads((d/('sfx-'+name+'.json')).read_text())
    art=json.loads((d/('art-'+name+'.json')).read_text())
    wad=json.loads((d/('wad-'+name+'.json')).read_text())
    assert audio['mode']=='mixed' and audio['count']==52
    assert art['adaptive_dither']=='bayer8'
    assert wad['all_non_reject_lumps_exact'] and wad['all_reject_lumps_exact']
    if valid[name] is None:
        assert wad['compressed_reject_lumps']==0 and not wad['enabled']
    else:
        assert wad['compressed_reject_lumps']>0 and wad['blocksize']==valid[name]
    binbytes=rom.read_bytes()
    raw=int((d/('payload-'+name+'.txt')).read_text())
    row=dict(name=name,wad_codec='REJECT_PackBits_'+str(valid[name]) if valid[name] else 'baseline_raw',
             rom_bytes=len(binbytes),rom_content_bytes=raw,
             wad_bytes=wad['packed_wad_bytes'],wad_bytes_saved=wad['saved_bytes_by_reject'],
             compressed_reject_lumps=wad['compressed_reject_lumps'],
             fps='UNTESTED',rom_sha256=hashlib.sha256(binbytes).hexdigest())
    print(row)
    rows.append(row)
base=next(x for x in rows if x['name']=='ctl-play')
for row in rows:
    assert row['wad_bytes']<=base['wad_bytes']
(d/'R34W-AUDIT.json').write_text(json.dumps(rows,indent=2)+'\n')
