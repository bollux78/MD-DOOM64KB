#!/usr/bin/env python3
from pathlib import Path
import importlib.util,subprocess,tempfile,shutil,json
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def load(path):
 s=importlib.util.spec_from_file_location('r93c_aux',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def verify(tables,out):
 # Regenerate with actual original tables, then the patched generator in isolation.
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);shutil.copytree(ROOT/'scripts',r/'scripts',ignore=shutil.ignore_patterns('*.wad','__pycache__'));(r/'src').mkdir();(r/'assets').mkdir()
  shutil.copy(tables,r/'src/r59_color_tables.h');shutil.copy(ROOT/'assets/r93c-compromise.json',r/'assets/r93c-compromise.json')
  for n in ('r79_shadow.inc','r91_shadow.inc'):shutil.copy(ROOT/'src'/n,r/'src'/n)
  module=load(r/'scripts/lab/gen_r79_shadow.py');module.generate(1)
  parse=module.parse;old=(r/'src/r79_shadow_tables.h').read_text()
  # apply_r93c expects a prepared builder; its only non-generator input is a stub.
  (r/'scripts/lab/build_r71a12mul_hud.py').write_text("prefix='r92-'\nvariant=('toggle', 1)\n")
  import os
  subprocess.run(['python3',str(ROOT/'scripts/lab/apply_r93c.py')],cwd=r,env={**os.environ,'R93C_CANDIDATE':'candidate'},check=True)
  module=load(r/'scripts/lab/gen_r79_shadow.py');module.generate(1);new=(r/'src/r79_shadow_tables.h').read_text()
  a=parse(old,'r79_pal').reshape(4,2,14,16);b=parse(new,'r79_pal').reshape(4,2,14,16);assert np.array_equal(a[:,:,1:],b[:,:,1:])
  assert np.array_equal(a[0],b[0]) and np.array_equal(a[3],b[3])
  assert np.count_nonzero(a[1]!=b[1])==4 and np.count_nonzero(a[2]!=b[2])==3
  subprocess.run(['python3','scripts/lab/test_r79_shadow.py','--generated'],cwd=r,check=True)
  subprocess.run(['python3','scripts/lab/gen_r91_shadow.py'],cwd=r,check=True)
  if out:
   out.mkdir(parents=True,exist_ok=True)
   for n in ('r79_shadow_tables.h','r79_shadow_report.json','r91_shadow_report.json'):shutil.copy(r/'src'/n,out/n)
  print('PASS exactly 7 p=0 CRAM slots; p>0 and inactive modes untouched; maps/joint tests passed')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--tables',type=Path,required=True);p.add_argument('--out',type=Path);a=p.parse_args();verify(a.tables,a.out)
