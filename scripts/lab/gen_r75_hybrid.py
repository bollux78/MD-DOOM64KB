#!/usr/bin/env python3
"""R75 hybrid: keep ALL L3 CRAM, companions, walls and sprites.
Create new flat-only even/odd LUTs aiming at the *perceived A2* flat colors.
All computation offline; no per-pixel renderer changes. Reconstructed targets.
"""
from pathlib import Path
import hashlib,json,re,runpy,subprocess,sys
import numpy as np
root=Path(__file__).resolve().parents[2]
staging=root/'dist'/'r75_a2_target'
staging.mkdir(parents=True,exist_ok=True)
def run(*args):
    subprocess.run([sys.executable,*map(str,args)],check=True,cwd=root)
run(root/'scripts/lab/gen_r52_claudio.py','--repo',root,'--out',staging,'--mode','near25','--zero-policy','allow','--no-preview')
run(root/'scripts/lab/gen_r53_micro.py','--repo',root,'--out',staging,'--profile','near25','--ratio','50')
run(root/'scripts/lab/gen_r74_flats.py','--source-dir',staging,'--profile','a','--policy','f2')
helper=runpy.run_path(str(root/'scripts/lab/gen_r74_flats.py'))
array=helper['array']
genpal=runpy.run_path(str(root/'scripts/genpal.py'))
math=runpy.run_path(str(root/'scripts/lab/gen_r52_claudio.py'))
def load(path):
    h=(path/'r52_ab_tables.h').read_text()
    p=(path/'r53_micro_tables.h').read_text()
    pal=[array(h,'r52_pal'+str(n)).reshape(14,16) for n in (0,1)]
    companions=[array(p,'r53_partner_'+name) for name in ('even','odd')]
    rgb=[np.asarray([[genpal['gen_to_rgb'](int(v)) for v in row] for row in bank],dtype=float) for bank in pal]
    effective=[math['avg_rgb'](colors,colors[:,partners]) for colors,partners in zip(rgb,companions)]
    return effective,companions
target_effective,_=load(staging)
target_luts=(staging/'r74_flat_tables.h').read_text()
target_codes=[array(target_luts,'r74_flat_'+side) for side in ('even','odd')]
target_mix=math['avg_rgb'](target_effective[0][0,target_codes[0]],target_effective[1][0,target_codes[1]])
target_lab=math['to_lab'](target_mix)
current_effective,_=load(root/'src')
original=np.asarray(genpal['decode_subpal'](genpal['load_playpal'](),0),dtype=float)
original_lab=math['to_lab'](original)
candidates=np.asarray([(i,j) for i in range(1,16) for j in range(1,16)],dtype=int)
even,odd=candidates.T
e0=current_effective[0][0,even];e1=current_effective[1][0,odd]
mixed=math['avg_rgb'](e0,e1)
mixed_lab=math['to_lab'](mixed)
between=math['delta_e'](e0,e1)
luma_gap=np.abs(math['luma'](e0)-math['luma'](e1))
policy=sys.argv[1]
assert policy in ('a2','near'),policy
out=np.empty((256,2),dtype=np.uint8);stats=[]
for c in range(256):
    de=np.linalg.norm(mixed_lab-target_lab[c],axis=1)
    native=np.linalg.norm(mixed_lab-original_lab[c],axis=1)
    chrom=np.linalg.norm(target_lab[c,1:])
    cand_chrom=np.linalg.norm(mixed_lab[:,1:],axis=1)
    hue=np.zeros(len(candidates),float)
    if chrom>14:
        cosine=(mixed_lab[:,1]*target_lab[c,1]+mixed_lab[:,2]*target_lab[c,2])/np.maximum(1e-6,cand_chrom*chrom)
        hue=chrom*np.maximum(0,.7-np.clip(cosine,-1,1)) + 2*np.maximum(0,.45*chrom-cand_chrom)
    wc,wn,wb,wl=((1.8,.3,1.0,.15) if policy=='a2' else (1.0,.3,2.8,.4))
    score=wc*de+wn*native+wb*between+wl*luma_gap+hue
    # Allow a range of representations but avoid flattening colors to gray.
    admissible=de<=max(18,1.8*float(de.min()))
    if not admissible.any():admissible[:]=True
    score[~admissible]=np.inf
    k=int(np.argmin(score))
    out[c]=candidates[k]
    stats.append(dict(c=c,even=int(even[k]),odd=int(odd[k]),distance_to_A2=float(de[k]),difference_between_columns=float(between[k]),luma_gap=float(luma_gap[k])))
lines=['/* R75 L3 walls and CRAM, A2-targeted flat-only remap. */','#ifndef R75_HYBRID_FLATS_H','#define R75_HYBRID_FLATS_H','#include <stdint.h>']
for side,i in [('even',0),('odd',1)]:
    lines.append('static const uint8_t r75_flat_'+side+'[256]={'+','.join(map(str,out[:,i]))+'};')
lines.append('#endif')
dest=root/'src/r75_hybrid_flats.h';dest.write_text('\n'.join(lines)+'\n')
report=dict(policy=policy,reference='reconstructed N25A-M50 F2 via R52/R53/R74, not historical ROM identity',renderer='L32F-M50 with F3 walls/CRAM',sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),zero_count=int((out==0).sum()),rows=stats)
(root/'src/r75_hybrid_report.json').write_text(json.dumps(report,indent=2)+'\n')
print('R75 hybrid generated',policy,'sha256',report['sha256'],flush=True)
