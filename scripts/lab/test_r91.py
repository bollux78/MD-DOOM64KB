#!/usr/bin/env python3
from pathlib import Path
import os,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 base=Path(td)/'base';shutil.copytree(ROOT,base,ignore=shutil.ignore_patterns('.git','dist','__pycache__'))
 for f,e in [('apply_r81.py',{}),('apply_r80_performance.py',{'R80_EXPERIMENTS':'P1+F1'}),('apply_r83.py',{'R83_CANDIDATE':'sprites'}),('apply_r85.py',{'R85_CANDIDATE':'all'}),('apply_r88.py',{'R88_CANDIDATE':'ai'}),('apply_r89.py',{}),('apply_r90.py',{'R90_CANDIDATE':'control'})]:
  subprocess.run(['python3','scripts/lab/'+f],cwd=base,env={**os.environ,**e},check=True,stdout=subprocess.DEVNULL)
 for mode in ('control','sh1','sh2'):
  d=Path(td)/mode;shutil.copytree(base,d)
  subprocess.run(['python3','scripts/lab/apply_r91.py'],cwd=d,env={**os.environ,'R91_CANDIDATE':mode},check=True)
  s=(d/'src/r22_video.inc').read_text();assert 'r77_color_state={1,0,0}' in s
  assert 'r59_names[2]' in (d/'src/m_text.c').read_text()
  assert 'static uint8_t r89_ai_low=0;' in (d/'src/p_enemy2.c').read_text()
  if mode!='control':assert 'r91_joint[r59_color_mode-1u]' in s
print('PASS R91 chain, A2 default, A2/L3 labels, Normal AI and shadow hooks')
