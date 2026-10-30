#!/usr/bin/env python3
"""REVIEW ONLY: offline SH1 candidate. Never overwrites production headers.
Keeps SH1 block state/CRAM; refits only suspect horizontal pairs, p=0.
Color proxy deliberately matches R79, not a calibrated CRT/WAD reconstruction.
"""
from pathlib import Path
import argparse,csv,hashlib,json,runpy,re
import numpy as np
from gen_r91_shadow import emit
def arr(text,name):
 m=re.search(r"\b"+re.escape(name)+r"((?:\[\d+\])+)\s*=\s*\{(.*?)\};",text,re.S);assert m,name
 shape=tuple(map(int,re.findall(r"\d+",m[1])))
 return np.array([int(v,0) for v in re.findall(r"0x[0-9a-fA-F]+|\d+",m[2])],dtype=np.uint32).reshape(shape)
M=runpy.run_path(str(Path(__file__).with_name('gen_r52_claudio.py')))
lab,avg=M['to_lab'],M['avg_rgb']
BASE_SHA='38b4319bce37ac31164b757bd8525cf4d71015873b697d61c1aca6a6f1eb03cc'
def rgb(w):
 w=np.asarray(w);return np.stack([(w>>1)&7,(w>>5)&7,(w>>9)&7],-1)*255./7.
def effective(pal,partners,shadow=False):
 c=rgb(pal)*(.5 if shadow else 1.);return avg(c,c[np.asarray(partners,dtype=int)])
def de(a,b):return np.linalg.norm(a-b,axis=-1)
def beige_bad(target,actual):
 # A heuristic, exposed in the report. Does not ban genuinely beige targets.
 tc=np.linalg.norm(target[...,1:],axis=-1);ac=np.linalg.norm(actual[...,1:],axis=-1)
 yellow=(actual[...,2]>target[...,2]+8)&(actual[...,0]>target[...,0]+6)
 neutral=(tc<12)&(ac>18)&(actual[...,2]>10)
 return yellow|neutral

def fit_row(target,old_codes,colors,stripe_weight=.35,min_gain=1.):
 """target/colors in Lab, two banks. Return new codes and audit metrics.
 All tests apply per horizontal row; vertical partners cannot lose their detail.
 """
 ta,tb=np.asarray(target);oa,ob=map(int,old_codes)
 old=np.stack([colors[0,oa],colors[1,ob]])
 olderr=de(old,target);oldstripe=float(de(*old));targetstripe=float(de(ta,tb))
 badbeige=bool(np.any(beige_bad(np.asarray(target),old)))
 suspect=badbeige or oldstripe>targetstripe+6.
 info={'suspect':suspect,'beige':badbeige,'old_error':float(olderr.sum()),'old_stripe':oldstripe}
 if not suspect or oa==0 or ob==0:return (oa,ob),info
 aa,bb=np.meshgrid(np.arange(1,16),np.arange(1,16),indexing='ij');aa=aa.ravel();bb=bb.ravel()
 ca,cb=colors[0,aa],colors[1,bb]
 ea,eb=de(ca,ta),de(cb,tb);stripe=de(ca,cb)
 # A fixed-state correction may never worsen either sample's fidelity, increase
 # stripes, introduce suspect beige, or exceed original lightness/chroma errors.
 keep=(ea<=olderr[0]+1e-9)&(eb<=olderr[1]+1e-9)&(stripe<=oldstripe+1e-9)
 keep&=~beige_bad(ta,ca)&~beige_bad(tb,cb)
 for t,c,o in ((ta,ca,old[0]),(tb,cb,old[1])):
  keep&=np.abs(c[:,0]-t[0])<=abs(o[0]-t[0])+1e-9
  keep&=np.abs(np.linalg.norm(c[:,1:],axis=-1)-np.linalg.norm(t[1:]))<=abs(np.linalg.norm(o[1:])-np.linalg.norm(t[1:]))+1e-9
 score=ea+eb+stripe_weight*np.maximum(0,stripe-targetstripe)
 score=np.where(keep,score,np.inf);k=int(np.argmin(score))
 oldscore=float(olderr.sum()+stripe_weight*max(0,oldstripe-targetstripe))
 if not np.isfinite(score[k]) or score[k]>oldscore-min_gain:return (oa,ob),info
 info.update(new_error=float(ea[k]+eb[k]),new_stripe=float(stripe[k]))
 return (int(aa[k]),int(bb[k])),info

def rewrite_table(original,rows):
 """rows[state, target_a, target_b] -> final code pair; preserve every attribute."""
 original=np.asarray(original,dtype=np.uint32);assert original.shape==(65536,)
 result=original.copy();keys=np.arange(65536);ain=keys>>8;bin=keys&255
 state=((original>>31)==0).astype(int)
 for shift in (4,0):
  pair=rows[state,(ain>>shift)&15,(bin>>shift)&15]
  mask=np.uint32((15<<(16+shift))|(15<<shift))
  value=(pair[:,0].astype(np.uint32)<<(16+shift))|(pair[:,1].astype(np.uint32)<<shift)
  result=(result&~mask)|value
 assert np.array_equal(original&0xff00ff00,result&0xff00ff00)
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,default=Path('src/r59_color_tables.h'));p.add_argument('--shadow',type=Path,default=Path('src/r79_shadow_tables.h'));p.add_argument('--report',type=Path,default=Path('src/r79_shadow_report.json'));p.add_argument('--out',type=Path,required=True);p.add_argument('--stripe-weight',type=float,default=.35);p.add_argument('--min-gain',type=float,default=1.)
 a=p.parse_args();assert a.stripe_weight>=0 and a.min_gain>0
 source=a.base.read_bytes();assert hashlib.sha256(source).hexdigest()==BASE_SHA,'Wrong base LUTs'
 report=json.loads(a.report.read_text());assert report['strength']==1 and abs(report['cram_stretch']-1.35)<1e-9,'SH1 required'
 b=source.decode();s=a.shadow.read_text();pals=arr(s,'r79_pal');maps=arr(s,'r79_map');joint=arr(s,'r91_joint')
 assert pals.shape==(2,2,14,16) and joint.shape==(2,65536),'Run after gen_r91_shadow.py'
 audit=[];tables=[]
 for mode,prefix in enumerate(('r76_a','r76_l')):
  basepal=np.stack([arr(b,prefix+'_pal'+str(bank)).reshape(14,16)[0] for bank in (0,1)])
  part=np.stack([arr(b,prefix+'_pairs_'+side).reshape(16,2)[:,1] for side in ('even','odd')])
  boosted=np.minimum(7,np.floor(rgb(basepal)/255*7*1.35+.5)).astype(np.uint32)
  assert np.array_equal((boosted[:,:,0]<<1)|(boosted[:,:,1]<<5)|(boosted[:,:,2]<<9),pals[mode,:,0]),'CRAM is not SH1'
  target=np.stack([lab(effective(basepal[k],part[k])) for k in (0,1)])
  rows=np.zeros((2,16,16,2),dtype=np.uint8)
  for state in (0,1):
   colors=np.stack([lab(effective(pals[mode,k,0],part[k],bool(state))) for k in (0,1)])
   for ai in range(16):
    for bi in range(16):
     old=(int(maps[mode,0,state,0,ai*17])&15,int(maps[mode,0,state,1,bi*17])&15)
     if ai==0 or bi==0:new,info=old,{'suspect':False}
     else:new,info=fit_row(np.stack([target[0,ai],target[1,bi]]),old,colors,a.stripe_weight,a.min_gain)
     rows[state,ai,bi]=new
     if new!=old:audit.append(dict(mode=('A2','L3')[mode],state=state,input_a=ai,input_b=bi,old_a=old[0],old_b=old[1],new_a=new[0],new_b=new[1],**info))
  out=rewrite_table(joint[mode],rows)
  # Every row in the original table must really follow the independent maps;
  # otherwise fitting by row/state would silently modify unrelated entries.
  identity=rows.copy()
  for st in (0,1):
   for ai in range(16):
    for bi in range(16):identity[st,ai,bi]=(int(maps[mode,0,st,0,ai*17])&15,int(maps[mode,0,st,1,bi*17])&15)
  assert np.array_equal(rewrite_table(joint[mode],identity),joint[mode]),'Unexpected joint mapping'
  tables.append(out)
 table=np.stack(tables);a.out.mkdir(parents=True,exist_ok=False)
 (a.out/'r92_guarded_joint.h').write_text('/* REVIEW ONLY: same SH1 CRAM, p=0, fixed block states. */\n'+emit('r92_joint_guarded',table,'uint32_t'))
 with (a.out/'changed-rows.csv').open('w') as f:
  fields=['mode','state','input_a','input_b','old_a','old_b','new_a','new_b','suspect','beige','old_error','old_stripe','new_error','new_stripe'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(audit)
 summary={'status':'EXPERIMENTAL_NOT_VISUALLY_VALIDATED','model':'R79 RGB proxy, not measured MD DAC; target is quantized R91-control, not original WAD','source_sha256':hashlib.sha256(source).hexdigest(),'shadow_sha256':hashlib.sha256(a.shadow.read_bytes()).hexdigest(),'stripe_weight':a.stripe_weight,'min_gain':a.min_gain,'changed_rows':len(audit),'changed_blocks':[int(np.count_nonzero(table[i]!=joint[i])) for i in range(2)],'preserved':'CRAM, block shadow state, tile attributes, unsuspicious rows, transparent input rows; no runtime hook','table_bytes':int(table.nbytes),'scope':'p=0 only; p>0 fallback remains unchanged'}
 (a.out/'REPORT.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
