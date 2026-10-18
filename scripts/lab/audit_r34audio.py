#!/usr/bin/env python3
"""Independent R34-AUDIO compile audit: only SFX storage format may vary."""
import json,hashlib,sys
from pathlib import Path
d=Path(sys.argv[1]);names=sys.argv[2:]
variants={'ctl-play':('raw',0),'ctl-perf':('raw',0),
          'a2-play':('adpcm',2048),'a2-perf':('adpcm',2048),
          'a4-play':('adpcm',4096),'a4-perf':('adpcm',4096),
          'r4-play':('rle',4096),'r4-perf':('rle',4096)}
out=[]
for v in names:
    assert v in variants
    codec,buffer=variants[v]
    stem='doom-md-r34a-'+v
    rom=d/(stem+'.bin')
    elf=d/(stem+'.elf')
    flags=(d/('flags-'+stem+'.txt')).read_text()
    assert rom.exists() and elf.exists()
    required=['-DDOOM_R29_XGM2','-DDOOM_R29_MULTI','-DDOOM_R31_SFX',
              '-DDOOM_R25_MUSIC','-DDOOM_R30_NATIVE',
              '-DDOOM_R27_GROUP_SIDE','-DDOOM_R27_GROUP_LINE']
    assert all(f in flags for f in required),v
    assert '-DSFX_SILENT' not in flags,v
    assert ('-DTIMEDEMO' in flags)==v.endswith('perf'),v
    assert ('-DDOOM_R34_AUDIO' in flags)==(codec!='raw'),v
    assert ('-DDOOM_R34_PCM_2048' in flags)==(buffer==2048),v
    snd=json.loads((d/('sfx-'+v+'.json')).read_text())
    art=json.loads((d/('art-'+v+'.json')).read_text())
    assert art['adaptive_dither']=='bayer8'
    if codec=='raw':
        assert snd['mode']=='mixed' and snd['count']==52
        stored=original=snd['sum_pcm_bytes'];packed=0
    else:
        assert snd['codec']==codec and snd['buffer_bytes']==buffer,v
        assert snd['count']==52 and snd['compressed_count']>0
        assert snd['source_sha256']=='1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771'
        assert snd['raw_pcm_bytes']>snd['stored_pcm_bytes']
        assert snd['decoded_pcm_buffers_bytes']==2*buffer
        original=snd['raw_pcm_bytes']
        stored=snd['stored_pcm_bytes']
        packed=snd['compressed_count']
        assert all((x['codec']>0)==(x['packed']<x['raw']) for x in snd['samples'])
    image=rom.read_bytes()
    raw=int((d/('payload-'+v+'.txt')).read_text())
    row=dict(variant=v,codec=codec,buffer_per_pcm_channel=buffer,
             compressed_effects=packed,pcm_original_bytes=original,
             pcm_stored_bytes=stored,pcm_saved_bytes=original-stored,
             rom_bytes=len(image),rom_unpadded_bytes=raw,
             fits_2mib=len(image)<=2097152,
             SHA256=hashlib.sha256(image).hexdigest(),
             hardware_validation='PENDING')
    out.append(row)
    print(v,'ROM',len(image),'real',raw,'PCM saved',original-stored,
          'packed effects',packed)
assert len({x['pcm_original_bytes'] for x in out})==1
(d/'R34A-AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
