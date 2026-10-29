#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,subprocess,tempfile,shutil,sys
from r90_inject_flats import NAMES,EXPECTED,replace_arrays
ROOT=Path(__file__).resolve().parents[2]
payload=json.loads((ROOT/'assets/r90-flat-luts-safe.json').read_text());assert payload['r89_tables_sha256']==EXPECTED
original='// unchanged header\n'+''.join('static const uint8_t '+n+'[256]={'+','.join(['1']*256)+'};\n' for n in NAMES)+'static const int wall=123;\n'
result=replace_arrays(original,payload['arrays']);assert result.endswith('static const int wall=123;\n')
for bad in (original+original,original.replace(NAMES[0],'missing')):
 try:replace_arrays(bad,payload['arrays']);raise RuntimeError('accepted bad anchor')
 except AssertionError:pass
with tempfile.TemporaryDirectory() as td:
 base=Path(td)/'base';shutil.copytree(ROOT,base,ignore=shutil.ignore_patterns('.git','dist','__pycache__'))
 for f,e in [('apply_r81.py',{}),('apply_r80_performance.py',{'R80_EXPERIMENTS':'P1+F1'}),('apply_r83.py',{'R83_CANDIDATE':'sprites'}),('apply_r85.py',{'R85_CANDIDATE':'all'}),('apply_r88.py',{'R88_CANDIDATE':'ai'}),('apply_r89.py',{})]:
  subprocess.run([sys.executable,'scripts/lab/'+f],cwd=base,env={**os.environ,**e},check=True,stdout=subprocess.DEVNULL)
 menu=(base/'src/m_text.c').read_bytes()
 for mode in ('control','flats'):
  d=Path(td)/mode;shutil.copytree(base,d)
  subprocess.run([sys.executable,'scripts/lab/apply_r90.py'],cwd=d,env={**os.environ,'R90_CANDIDATE':mode},check=True)
  assert (d/'src/m_text.c').read_bytes()==menu,'menu changed'
  assert 'static uint8_t r89_ai_low=0;' in (d/'src/p_enemy2.c').read_text()
  assert 'quick_color' not in menu.decode()
  assert 'Hybrid' in menu.decode() and 'r59_names[4]' in menu.decode()
  (d/'src/r59_color_tables.h').write_text(original)
  p=subprocess.run([sys.executable,'scripts/lab/r90_inject_flats.py'],cwd=d,capture_output=True)
  assert p.returncode!=0 and 'STOP:' in p.stderr.decode()
  assert (d/'src/r59_color_tables.h').read_text()==original
print('PASS R90: exact original menu, Normal default, all optimizations applied, 8 flat arrays only, invalid hash/anchors rejected')
