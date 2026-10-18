#!/usr/bin/env python3
from pathlib import Path
import sys,subprocess,struct
from r21_heap_model import bend,model
root=Path(sys.argv[1]);report=[]
for variant in sys.argv[2:]:
 name='doom-md-r26-'+variant;b=(root/(name+'.bin')).read_bytes();flags=(root/('flags-'+name+'.txt')).read_text().split()
 assert len(b)<=(0x200000 if variant in ["control","play-control"] else 0x400000),(name,len(b))
 assert b[0x1b0:0x1b2]==b'RA'
 assert '-DDOOM_R22_SRAM_BLOCKLINKS' in flags
 assert ('-DTIMEDEMO' in flags)==(variant in ['control','episode-perf'])
 assert ('-DDOOM_R24_EPISODE' in flags)==(variant not in ['control','play-control'])
 assert ('-DDOOM_R23_MAPMEM' in flags)==(variant not in ['control','play-control'])
 pixel=variant=='episode-p4'
 assert ('-DDOOM_R22_PIXEL4' in flags)==pixel
 m=model(bend(root/(name+'.elf')),alloc=2432 if pixel else 2128,no_init=True)
 assert not m['boot_fail'] and m['after']>=0,(name,m)
 report.append(f'{name}: bytes={len(b)}, heap={m}')
(root/'heap-budget.txt').write_text('\n'.join(report)+'\n');print('\n'.join(report))

# Audit every music byte and every interrupt/code/constant byte below SRAM window.
import json
for variant in sys.argv[2:]:
 if variant in ['control','play-control']:continue
 name='doom-md-r26-'+variant;elf=(root/(name+'.elf')).read_bytes()
 off=struct.unpack_from('>I',elf,32)[0];sz,n=struct.unpack_from('>HH',elf,46)
 hs=[struct.unpack_from('>10I',elf,off+i*sz) for i in range(n)];syms={}
 for h in hs:
  if h[1]!=2:continue
  st=hs[h[6]];strings=elf[st[4]:st[4]+st[5]]
  for p in range(h[4],h[4]+h[5],h[9]):
   k,v,size=struct.unpack_from('>III',elf,p);syms[strings[k:].split(b'\0',1)[0].decode()]=(v,size)
 assert syms['_etext'][0]<0x200000,(name,'code / constants above SRAM aperture')
 rom=(root/(name+'.bin')).read_bytes();music=[]
 for label in ['e1m'+str(i) for i in range(1,10)]+['intro','inter','victor','silent']:
  a=syms['bgm_'+label][0];size=syms['bgm_'+label+'_size'][0]
  assert a%256==0 and a+size<=0x200000,(name,label,a,size)
  music.append(dict(track=label,address=a,bytes=size))
 wad=[v for k,v in syms.items() if k.startswith('doom_iwad')];assert len(wad)==1
 assert wad[0][0]>=max(t['address']+t['bytes'] for t in music),(name,'WAD must follow all music')
 assert '-DDOOM_R25_MUSIC' in (root/('flags-'+name+'.txt')).read_text()
 (root/('music-layout-'+variant+'.json')).write_text(json.dumps(dict(music=music,wad_address=wad[0][0],wad_bytes=wad[0][1],code_end=syms['_etext'][0]),indent=2)+'\n')
 print(name,'music and code below 2 MiB; WAD in switchable ROM')

# Match the exact recorded commands and all nine E1M1 lumps across architectures.
from convert_r24_episode import read_wad,map_at
import hashlib
def wad(variant):
 b=(root/('doom-md-r26-'+variant+'.bin')).read_bytes();return read_wad(b[b.index(b'IWAD'):],True)
a=wad('control');b=wad('episode-perf')
assert dict(a)['DEMO3']==dict(b)['DEMO3']
assert map_at(a,'E1M1')==map_at(a,'E1M7')==map_at(b,'E1M1')
(root/'matched-benchmark.json').write_text(json.dumps(dict(demo='DEMO3',header_map=7,effective_map=1,demo_sha256=hashlib.sha256(dict(a)['DEMO3']).hexdigest(),map_lumps={k:hashlib.sha256(v).hexdigest() for k,v in map_at(a,'E1M1').items()}),indent=2)+'\n')
print('PASS identical DEMO3 and E1M1 geometry/objects across control and perf')
