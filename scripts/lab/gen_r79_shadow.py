#!/usr/bin/env python3
"""R79 experimental 8x8 normal/shadow blocks; ROM-only maps, no highlight.
Targets are R77 effective pair colors, not recovered original WAD pixels.
"""
from pathlib import Path
import argparse,csv,json,re,runpy
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
math=runpy.run_path(str(ROOT/'scripts/lab/gen_r52_claudio.py'))
avg,lab=math['avg_rgb'],math['to_lab']

def parse(text,name):
 m=re.search(r'\b'+name+r'(?:\[\d+\])+\s*=\s*\{(.*?)\};',text,re.S);assert m,name
 return np.array([int(v,0) for v in re.findall(r'0x[\da-fA-F]+|\d+',m[1])],int)
def rgb(w):return np.stack([(w>>1)&7,(w>>5)&7,(w>>9)&7],-1)*255./7.
def emit(name,a):
 a=np.asarray(a);dims=''.join('['+str(n)+']' for n in a.shape)
 def nest(v):return '{'+','.join(nest(x) if np.ndim(x) else str(int(x)) for x in v)+'}'
 return 'static const uint16_t '+name+dims+'='+nest(a)+';\n'
def generate(strength):
 text=(ROOT/'src/r59_color_tables.h').read_text();gain={1:1.35,2:1.75}[strength]
 palettes=[];maps=[];costs=[];reports=[];pairsrows=[]
 for name,prefix in [('Hybrid Blue+','r77_h'),('A2 Full','r76_a'),('L3 Detail','r76_l'),('HN Smooth','r76_l')]:
  pal=np.array([parse(text,prefix+'_pal'+str(b)).reshape(14,16) for b in (0,1)])
  partners=np.array([parse(text,prefix+'_pairs_'+side).reshape(16,2)[:,1] for side in ('even','odd')])
  components=np.stack([(pal>>1)&7,(pal>>5)&7,(pal>>9)&7],-1)
  boosted=np.minimum(7,np.floor(components*gain+.5)).astype(int)
  words=(boosted[...,0]<<1)|(boosted[...,1]<<5)|(boosted[...,2]<<9)
  palettes.append(words)
  target=np.array([avg(rgb(pal[b]),rgb(pal[b])[:,partners[b]]) for b in (0,1)])
  candN=np.array([avg(rgb(words[b]),rgb(words[b])[:,partners[b]]) for b in (0,1)])
  # Applying shadow before spatial averaging is essential.
  candS=np.array([avg(rgb(words[b])*.5,rgb(words[b])[:,partners[b]]*.5) for b in (0,1)])
  cand=np.stack([candN,candS],1) # bank,state,palette,code,rgb
  error=((lab(target)[:,None,:,:,None,:]-lab(cand)[:,:,:,None,:,:])**2).sum(-1)
  error[:,:,:,:,0]=1e9 # opaque samples must not become transparent
  code=np.argmin(error,axis=-1)
  code[:,:,:,0]=0
  err=np.take_along_axis(error,code[...,None],axis=-1)[...,0];err[:,:,:,0]=0
  # Fixed point costs: pair sums bounded to 65534, runtime sums widened.
  err=np.minimum(32767,np.floor(err*4+.5)).astype(int)
  pm=[];pc=[]
  for p in range(14):
   sm=[];sc=[]
   for state in range(2):
    bm=[];bc=[]
    for b in range(2):
     packed=np.arange(256);hi,lo=packed>>4,packed&15
     attrs=0x100 if b==0 else 0x2200
     if b==0 and state==0:attrs|=0x8000
     bm.append(attrs|(code[b,state,p,hi]<<4)|code[b,state,p,lo])
     bc.append(err[b,state,p,hi]+err[b,state,p,lo])
    sm.append(bm);sc.append(bc)
   pm.append(sm);pc.append(sc)
  maps.append(pm);costs.append(pc)
  ii,jj=np.meshgrid(np.arange(1,16),np.arange(1,16),indexing='ij');ii,jj=ii.ravel(),jj.ravel()
  base={tuple(x) for x in np.round(avg(target[0,0,ii],target[1,0,jj]),6)}
  sets=[]
  for state,c in enumerate([candN,candS]):
   mix=avg(c[0,0,ii],c[1,0,jj]);sets.append({tuple(x) for x in np.round(mix,6)})
   for k,(i,j) in enumerate(zip(ii,jj)):
    pairsrows.append([name,'NN' if state==0 else 'SS',int(i),int(j),*mix[k].tolist()])
  c=np.asarray(pc[0]);n=c[0,0,:,None]+c[0,1,None,:];s=c[1,0,:,None]+c[1,1,None,:]
  selected=np.asarray(code[:,:,0]);used=[]
  for state in range(2):
   used.append([len(set(selected[b,state,1:].tolist())) for b in range(2)])
  mapped_sets=[]
  for state,c in enumerate([candN,candS]):
   mapped_sets.append({tuple(x) for x in np.round(avg(c[0,0,selected[0,state,ii]],c[1,0,selected[1,state,jj]]),6)})
  reports.append(dict(mapped_normal_means=len(mapped_sets[0]),mapped_shadow_means=len(mapped_sets[1]),
    mapped_union=len(mapped_sets[0]|mapped_sets[1]),profile=name,normal_pair_means=len(sets[0]),shadow_pair_means=len(sets[1]),
    normal_shadow_union=len(sets[0]|sets[1]),baseline_pair_means=len(base),
    means_absent_from_R77=len((sets[0]|sets[1])-base),mapped_codes_per_bank=used,
    synthetic_blocks_shadow=int((s<n).sum()),synthetic_blocks_total=65536,
    mean_best_block_cost=float(np.minimum(n,s).mean()/4),
    palette0_mapping={state: selected[:,i,:].tolist() for i,state in enumerate(('normal','shadow'))}))
 header='/* R79 ROM only; mode,state,bank,packed R77 codes. */\n'+emit('r79_pal',palettes)+emit('r79_map',maps)+emit('r79_cost',costs)
 (ROOT/'src/r79_shadow_tables.h').write_text(header)
 report=dict(strength=strength,cram_stretch=gain,highlight=False,block_pixels=[8,8],
  intensity='DAC N(c)=2c, S(c)=c; RGB proxy uses shadow=normal/2 BEFORE M50 averaging',
  target='R77 already quantized colors; does not recover discarded texture information',
  geometry='B priority always 0. A priority controls both visible 4px halves of its 8px tile, including A transparent half. H32/H40 scroll difference remains 4px.',
  limitation='One state for four logical 4x4 samples. Candidate count is not simultaneous screen colors. Extra CPU postpass; no FPS claim.',profiles=reports)
 (ROOT/'src/r79_shadow_report.json').write_text(json.dumps(report,indent=2)+'\n')
 with (ROOT/'src/r79_shadow_pairs.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['profile','mode','even_code','odd_code','mean_R_proxy','mean_G_proxy','mean_B_proxy']);w.writerows(pairsrows)
 print(json.dumps(report))
 return np.asarray(maps),np.asarray(costs)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--strength',type=int,choices=(1,2),required=True);generate(p.parse_args().strength)
