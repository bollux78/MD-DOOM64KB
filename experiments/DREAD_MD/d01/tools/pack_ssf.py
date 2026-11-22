"""Prepare independent map banks linked at the fixed2MiB runtime window.
Code, music and UI remain in the first2MiB. Bank changes occur only at map load.
"""
from pathlib import Path
import sys,subprocess,re,os,json,shutil
from pack_episode import entries,numbers,initializer
out=Path(sys.argv[1]);maps=[Path(p) for p in sys.argv[2:]];tools=Path(__file__).resolve().parent;src=tools.parent/'src';gdk=Path(os.environ['GDK']);tc=os.environ.get('DREAD_TC',str(gdk/'bin/m68k-elf-'))
manifest=[];definitions=[];physical=0x200000;maxcounts=[0]*6;maxactors=1;maxpvs=0
for i,m in enumerate(maps):
 d=out.parent/'ssf-banks'/str(i);d.mkdir(parents=True,exist_ok=True)
 subprocess.run(['python3',str(tools/'pack_episode.py'),str(d),str(m)],check=True)
 subprocess.run(['python3',str(tools/'gen_sky.py'),str(tools/'sky_e1doom_256x72_pal.png'),str(d/'episode.c'),str(d/'sky.c')],check=True)
 source=(d/'episode.c').read_text()+'\n'+(d/'sky.c').read_text();(d/'bank.c').write_text(source)
 (d/'bank.ld').write_text('OUTPUT_ARCH(m68k)\nSECTIONS { .map 0x200000 : { *(.rodata*) *(.data*) } /DISCARD/ : { *(.comment) *(.eh_frame*) } }\n')
 subprocess.run([tc+'gcc','-m68000','-ffreestanding','-fno-pic','-O2','-DSGDK_GCC','-DDREAD_EPISODE','-I'+str(src),'-I'+str(d),'-I'+str(gdk/'inc'),'-c',str(d/'bank.c'),'-o',str(d/'bank.o')],check=True)
 subprocess.run([tc+'ld','-T',str(d/'bank.ld'),str(d/'bank.o'),'-o',str(d/'bank.elf')],check=True)
 subprocess.run([tc+'objcopy','-O','binary',str(d/'bank.elf'),str(d/'bank.bin')],check=True)
 syms={}
 for line in subprocess.check_output([tc+'nm',str(d/'bank.elf')],text=True).splitlines():
  c=line.split()
  if len(c)==3:syms[c[2]]=int(c[0],16)
 desc=re.search(r'const DreadMap episode_maps\[\] = \{(\{.*?\})\};',source,re.S)[1][1:-1]
 def address(match):
  name=match[0]
  return '(void*)0x%x'%syms[name] if name in syms else name
 desc=re.sub(r'\b(?:ep\d+_\w+)\b',address,desc)
 extras=','.join('(void*)0x%x'%syms[name] for name in ['tex_blob','spr_blob','episode_pvs','tex_columns','sky_blob','md_palette'])
 definitions.append('{'+desc+','+extras+'}')
 size=(d/'bank.bin').stat().st_size
 if size>0x200000:raise ValueError((m,size,'map exceeds2MiB window'))
 manifest.append({'map':m.name,'physical':physical,'bank':physical//0x80000,'bytes':size,'file':str(d/'bank.bin')})
 physical+=(size+0x7ffff)&~0x7ffff
 data=entries(m/'mapdata.c');counts=numbers(data['map_counts']);maxcounts=[max(a,b) for a,b in zip(maxcounts,counts)];maxactors=max(maxactors,sum(bool(x&1) for x in numbers(data['map_things'])[4::5]))
 v=entries(m/'pvs.c');maxpvs=max(maxpvs,numbers(v['pvs_nbytes'])[0]+numbers(v['pvs_sbytes'])[0])
fixed=['#define DREAD_EPISODE_DATA','#include "mapdata.h"']
fixed.append(entries(maps[0]/'mapdata.c')['sintab'])
fixed+=['const DreadMap episode_maps[9]={'+','.join(definitions)+'};','const uint16_t episode_map_count=9;','const DreadMap *dread_map=episode_maps;','const uint8_t ssf_map_banks[9]={'+','.join(str(x['bank']) for x in manifest)+'};']
(out/'episode.c').write_text('\n'.join(fixed)+'\n')
(out/'mapcounts.h').write_text('\n'.join(['#define MAP_NVERTS '+str(maxcounts[0]),'#define MAP_NSECTORS '+str(maxcounts[4]),'#define MAP_NSUBS '+str(maxcounts[2]),'#define MAP_NACTORS '+str(maxactors),'#define EP_PVS_BYTES '+str(maxpvs)])+'\n')
(out/'ssf-layout.json').write_text(json.dumps(manifest,indent=2));print('SSF physical end',hex(physical),'maps',len(manifest))
if physical>15*1024*1024:raise ValueError('ROM exceeds15MiB')
