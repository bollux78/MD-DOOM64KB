#!/usr/bin/env python3
"""Offline only. Jointly requantize ideal SH1 normal/shadow slot outputs.
Uniform state weights are hypotheses, NOT observed usage frequencies.
Does not edit tables consumed by any ROM build.
"""
from pathlib import Path
import argparse,json,csv,runpy
import numpy as np
from gen_r79_shadow import parse,rgb
M=runpy.run_path(str(Path(__file__).with_name('gen_r52_claudio.py')));lab=M['to_lab']
def hue(x):return np.degrees(np.arctan2(x[...,2],x[...,1]))
def hd(a,b):return np.abs((a-b+180)%360-180)
def main():
 p=argparse.ArgumentParser();p.add_argument('--tables',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--normal-weight',type=float,default=.5);a=p.parse_args();assert 0<=a.normal_weight<=1
 s=a.tables.read_text();grid=np.array(np.meshgrid(np.arange(8),np.arange(8),np.arange(8),indexing='ij')).reshape(3,-1).T;words=(grid[:,0]<<1)|(grid[:,1]<<5)|(grid[:,2]<<9);cn=grid*255./7;cs=cn*.5;ln,ls=lab(cn),lab(cs);rows=[];pals=[]
 for mode in ('r76_a','r76_l'):
  banks=[]
  for bank in (0,1):
   old=parse(s,mode+'_pal'+str(bank)).reshape(14,16);out=old.copy()
   for effect in range(14):
    for slot in range(16):
     original=rgb(old[effect,slot]);ideal=np.minimum(255,original*1.35)
     targetN,targetS=lab(ideal),lab(ideal*.5)
     oldgrid=np.minimum(7,np.floor(original/255*7*1.35+.5));oldlab=lab(oldgrid*255/7)
     score=a.normal_weight*np.sum((ln-targetN)**2,axis=1)+(1-a.normal_weight)*np.sum((ls-targetS)**2,axis=1)
     # Guard hue against the continuous ideal; for near neutrals constrain chroma.
     chroma=np.linalg.norm(targetN[1:]);valid=(hd(hue(ln),hue(targetN))<=max(8.,float(hd(hue(oldlab),hue(targetN))))) if chroma>8 else (np.linalg.norm(ln[:,1:],axis=1)<=max(8.,np.linalg.norm(oldlab[1:])))
     valid&=np.abs(ln[:,0]-targetN[0])<=max(6.,abs(oldlab[0]-targetN[0]))
     if slot==0:k=int(np.argmin(np.sum((grid-oldgrid)**2,axis=1)))
     else:k=int(np.argmin(np.where(valid,score,np.inf))) if valid.any() else int(np.argmin(score))
     out[effect,slot]=words[k]
     rows.append(dict(mode=mode,bank=bank,effect=effect,slot=slot,original=int(old[effect,slot]),channel_round=int((int(oldgrid[0])<<1)|(int(oldgrid[1])<<5)|(int(oldgrid[2])<<9)),candidate=int(words[k]),old_L=float(oldlab[0]),new_L=float(ln[k,0]),ideal_L=float(targetN[0]),old_hue=float(hue(oldlab)),new_hue=float(hue(ln[k])),ideal_hue=float(hue(targetN)),old_chroma=float(np.linalg.norm(oldlab[1:])),new_chroma=float(np.linalg.norm(ln[k,1:]))))
   banks.append(out.tolist())
  pals.append(banks)
 a.out.mkdir(parents=True,exist_ok=False)
 (a.out/'candidate-palettes.json').write_text(json.dumps({'palettes':pals,'normal_weight':a.normal_weight,'targets':'normal=continuous min(255, original*1.35), shadow=ideal_normal/2','model':'R79 sRGB/Lab proxy; state usage not measured','status':'STUDY ONLY; maps/costs/joint decisions must be regenerated before visual test; no block-change counts computed'},indent=2)+'\n')
 with (a.out/'slots.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print('Study only:',len(rows),'slots; no ROM/header modified')
if __name__=='__main__':main()
