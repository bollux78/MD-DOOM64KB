#!/usr/bin/env python3
"""Create the human-test ZIP only after CI, ROM SHA256 and CPU checks pass."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,zipfile
p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);p.add_argument('cpu',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
assert (a.artifacts/'COMPLETE.txt').is_file()
cpu=json.loads((a.cpu/'summary.json').read_text());assert len(cpu)==4
assert all([f['hash'] for f in v['frames']]==[f['hash'] for f in cpu['base']['frames']] for v in cpu.values())
for line in (a.artifacts/'SHA256SUMS').read_text().splitlines():
 sha,name=line.split();f=a.artifacts/Path(name).name
 assert hashlib.sha256(f.read_bytes()).hexdigest()==sha,f
variants=['control','play-control','episode-perf','group-perf','group-play','low-window','low-fixed','low-group','low-play']
stage=a.output.parent/'r28-pacote';stage.mkdir(exist_ok=True)
for v in variants:
 name='doom-md-r28-'+v
 for src,dst in [(name+'.bin','ROMs/'+name+'.bin'),(name+'.elf','ELFs/'+name+'.elf'),('flags-'+name+'.txt','evidencias/flags-'+name+'.txt'),('build-'+name+'.log','evidencias/build-'+name+'.log')]:
  target=stage/dst;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.artifacts/src,target)
for f in a.artifacts.iterdir():
 if f.suffix in ['.json','.txt'] and not f.name.startswith(('flags-','SHA256')) and 'cpu-' not in f.name:
  dest=stage/('LEIA-ME.md' if f.name=='LEIA-ME.md' else 'evidencias/'+f.name);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
shutil.copyfile(a.artifacts/'LEIA-ME.md',stage/'LEIA-ME.md')
shutil.copyfile(a.cpu/'summary.json',stage/'evidencias/CPU-COMPARISON.json')
files=sorted(f for f in stage.rglob('*') if f.is_file() and f.name!='SHA256SUMS')
(stage/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(stage).as_posix()+'\n' for f in files))
tmp=a.output.with_suffix('.tmp')
with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
 for f in sorted(stage.rglob('*')):
  if f.is_file():z.write(f,f.relative_to(stage))
with zipfile.ZipFile(tmp) as z:
 assert z.testzip() is None
 for line in z.read('SHA256SUMS').decode().splitlines():
  sha,name=line.split();assert hashlib.sha256(z.read(name)).hexdigest()==sha
 assert len([f for f in z.namelist() if f.endswith('.bin')])==9
os.replace(tmp,a.output)
print(a.output,a.output.stat().st_size,hashlib.sha256(a.output.read_bytes()).hexdigest())
