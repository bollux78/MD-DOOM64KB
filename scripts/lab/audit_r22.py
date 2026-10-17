#!/usr/bin/env python3
import pathlib,json,hashlib,struct,importlib.util,sys
r=pathlib.Path(__file__).resolve().parents[2];d=pathlib.Path(sys.argv[1])
spec=importlib.util.spec_from_file_location('heap',r/'scripts/lab/r21_heap_model.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
names=['control','p4-fixed','play-fixed','solid','diag-solid','play-solid','solid-lut','play-lut','pattern-lut']
names=sys.argv[2:] or names
assert len(names)==len(set(names)) and set(names)<=set(['control','play-control','p4-fixed','play-fixed','solid','diag-solid','play-solid','solid-lut','play-lut','pattern-lut'])
assert {p.stem for p in d.glob('*.bin')}=={'doom-md-r22c-'+n for n in names}
rows=[];manifest=[]
for n in names:
 stem='doom-md-r22c-'+n;p=d/(stem+'.bin');b=p.read_bytes();f=set((d/('flags-'+stem+'.txt')).read_text().split());pix=n not in ['control','play-control']
 assert b[0x120:0x150].decode().strip()==stem
 assert 512<=len(b)<=0x200000 and struct.unpack_from('>I',b,0x1a4)[0]>=len(b)-1
 assert '-DDOOM_R21_NO_VDP_INIT' in f and '-DDOOM_R20_VBLANK_VIDEO' in f
 assert ('-DTIMEDEMO' in f)==(n in ['control','p4-fixed','solid','diag-solid','solid-lut'])
 assert ('-DDOOM_R20_STACKGUARD' in f)==(n=='diag-solid')
 assert ('-DDOOM_R22_PATTERN' in f)==(n=='pattern-lut')
 assert ('-DDOOM_R22_PIXEL4' in f)==pix
 assert ('-DDOOM_R22_SOLID_TILES' in f)==(n in ['solid','diag-solid','play-solid','solid-lut','play-lut','pattern-lut'])
 assert ('-DDOOM_R22_PAIR_LUT' in f)==(n in ['solid-lut','play-lut','pattern-lut'])
 for flag in ['-DDOOM_R20_FLAT_INLINE','-DDOOM_R20_REG_COLUMNS','-DDOOM_R20_PIXEL_ADDX','-DDOOM_CELL_LUT']:
  assert (flag in f)==(not pix),(n,flag)
 assert ('-DVIEWWINDOWWIDTH=76' if pix else '-DVIEWWINDOWWIDTH=38') in f
 assert ('-DVIEWWINDOWHEIGHT=44' if pix else '-DVIEWWINDOWHEIGHT=22') in f
 elf=d/(stem+'.elf');assert elf.stat().st_size
 m=h.model(h.bend(elf),alloc=2432 if pix else 2128,no_init=True)
 assert not m['boot_fail'] and m['after']>=256,(n,m)
 rows.append(f'{n}: '+json.dumps(m))
 manifest.append(dict(name=p.name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),pixel4=pix))
(d/'heap-report.txt').write_text('\n'.join(rows)+'\n')
(d/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS R22c selected ROMs, identities/flags, boot font budget and runtime openings/snapshot allocation')
