#!/usr/bin/env python3
"""Offline real-table study: requantize SH1, regenerate all maps and joint LUTs.
No game source/header edits, no compiler toolchain for ROM, no runtime changes.
"""
from pathlib import Path
import argparse,tempfile,shutil,subprocess,sys,importlib.util,json,hashlib
import numpy as np
from gen_r91_shadow import arr
ROOT=Path(__file__).resolve().parents[2]
def module(path):
 spec=importlib.util.spec_from_file_location('cram_eval_aux',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser();p.add_argument('--tables',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.tables=a.tables.resolve();a.out.mkdir(parents=True,exist_ok=False)
 sha=hashlib.sha256(a.tables.read_bytes()).hexdigest();assert sha=='38b4319bce37ac31164b757bd8525cf4d71015873b697d61c1aca6a6f1eb03cc','Unexpected real tables'
 subprocess.run([sys.executable,str(ROOT/'scripts/lab/r92_cram_study.py'),'--tables',str(a.tables),'--out',str(a.out/'quantization')],check=True)
 payload=json.loads((a.out/'quantization/candidate-palettes.json').read_text());candidate=np.array(payload['palettes'])
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);shutil.copytree(ROOT/'scripts',r/'scripts',ignore=shutil.ignore_patterns('__pycache__','*.wad'));(r/'src').mkdir();shutil.copy(a.tables,r/'src/r59_color_tables.h')
  for name in ('r79_shadow.inc','r91_shadow.inc'):shutil.copy(ROOT/'src'/name,r/'src'/name)
  # Same generator and model; only the CRAM quantization assignment differs.
  original=(r/'scripts/lab/gen_r79_shadow.py').read_text()
  anchor='  palettes.append(words)';assert original.count(anchor)==1
  extra="  if prefix in ('r76_a','r76_l'):\n   words=np.array("+repr(candidate.tolist())+")[0 if prefix=='r76_a' else 1]\n"
  histories=[]
  for label,source in (('baseline',original),('candidate',original.replace(anchor,extra+anchor))):
   d=a.out/label;d.mkdir();(r/'scripts/lab/gen_r79_shadow.py').write_text(source)
   with (d/'generation.log').open('w') as log:
    for cmd in ([sys.executable,'scripts/lab/gen_r79_shadow.py','--strength','1'],[sys.executable,'scripts/lab/test_r79_shadow.py','--generated'],[sys.executable,'scripts/lab/gen_r91_shadow.py']):subprocess.run(cmd,cwd=r,check=True,stdout=log,stderr=subprocess.STDOUT)
   h=(r/'src/r79_shadow_tables.h').read_text();histories.append(h)
   for n in ('r79_shadow_tables.h','r79_shadow_report.json','r91_shadow_report.json'):shutil.copy(r/'src'/n,d/n)
  old,new=histories;op,npal=arr(old,'r79_pal'),arr(new,'r79_pal');oj,nj=arr(old,'r91_joint'),arr(new,'r91_joint')
  rows=[]
  for m,label in enumerate(('A2','L3')):
   a0,b0=oj[m],nj[m]
   rows.append({'mode':label,'cram_words_changed_all_effects':int(np.count_nonzero(op[m]!=npal[m])),'cram_words_changed_p0':int(np.count_nonzero(op[m,:,0]!=npal[m,:,0])),'joint_entries_changed_p0':int(np.count_nonzero(a0!=b0)),'shadow_state_changed_p0':int(np.count_nonzero((a0>>31)!=(b0>>31))),'shadow_blocks_before_p0':int(np.count_nonzero((a0>>31)==0)),'shadow_blocks_after_p0':int(np.count_nonzero((b0>>31)==0))})
  assert np.array_equal(op[:,:,:,0],npal[:,:,:,0]),'Protected transparent slot changed'
  result={'status':'OFFLINE_CANDIDATE_NOT_VISUALLY_APPROVED','base_tables_sha256':sha,'normal_shadow_weights':[.5,.5],'weights_measured':False,'model':'same R79 sRGB/Lab proxy; not measured CRT DAC','rows':rows,'limits':'unweighted enumeration of all 65536 input keys; not observed screen frequency; target is continuous boosted CRAM, not original texture RGB','tests':'original R79 C tests across 4 profiles x14 effects; original R91 exhaustive checks plus 80 actual C frame comparisons for both baseline and candidate','runtime_table_bytes':524288,'rom_built':False}
  (a.out/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
