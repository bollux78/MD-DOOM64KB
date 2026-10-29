#!/usr/bin/env python3
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
def fn(s,name):
 a=s.index(name);i=s.index('{',a);j=i+1;n=1
 while n:n+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
with tempfile.TemporaryDirectory() as tmp:
 b=Path(tmp)/'base';shutil.copytree(ROOT,b,ignore=shutil.ignore_patterns('.git','dist','__pycache__'))
 for script,env in [('apply_r81.py',{}),('apply_r80_performance.py',{'R80_EXPERIMENTS':'P1+F1'}),('apply_r83.py',{'R83_CANDIDATE':'sprites'}),('apply_r85.py',{'R85_CANDIDATE':'all'})]:
  subprocess.run(['python3','scripts/lab/'+script],cwd=b,env={**os.environ,**env},check=True,stdout=subprocess.DEVNULL)
 for mode in ('control','ai'):
  d=Path(tmp)/mode;shutil.copytree(b,d)
  subprocess.run(['python3','scripts/lab/apply_r88.py'],cwd=d,env={**os.environ,'R88_CANDIDATE':mode},check=True)
  s=(d/'src/g_game.c').read_text();hdr=s.split('static const byte __far* G_ReadDemoHeader')[1].split('static void ExtractFileBase')[0]
  assert 'map = 1;' in hdr and 'if (_g_timingdemo) map = D_R88_BenchmarkMap();' in hdr
  assert (d/'src/r_sky.c').read_bytes()==(b/'src/r_sky.c').read_bytes()
  s=(d/'src/d_main.c').read_text();m=(d/'src/m_text.c').read_text()
  c=Path(tmp)/'check.c';c.write_text('#include <stdint.h>\n#include <assert.h>\nstatic uint8_t r88_bench_map=1;static int clear,started;\nstatic void M_ClearMenus(void){clear++;}static void D_R50_BenchmarkStart(void){started++;}\n'+fn(s,'void D_R88_SelectBenchmarkMap(')+fn(s,'uint8_t D_R88_BenchmarkMap(')+fn(m,'static void M_R88RunSelected(')+'''int main(void){assert(D_R88_BenchmarkMap()==1);M_R88RunSelected(1);assert(D_R88_BenchmarkMap()==7&&clear==1&&started==1);M_R88RunSelected(0);assert(D_R88_BenchmarkMap()==1&&clear==2&&started==2);return 0;}''')
  subprocess.run(['cc','-O2',str(c),'-o',str(Path(tmp)/'check')],check=True);subprocess.run([str(Path(tmp)/'check')],check=True)
  builder=(d/'scripts/lab/build_r71a12mul_hud.py').read_text();assert "for suffix,mode in (('pl','play'),)" in builder and 'assert len(records) == 1' in builder
  assert 'E1M1 Hangar' in m and 'E1M7 Computer Station' in m
  print('PASS',mode,'PLAY selectors, PERF map=1 branch, original sky, PLAY-only builder')
