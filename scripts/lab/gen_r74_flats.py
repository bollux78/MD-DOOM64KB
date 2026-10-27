#!/usr/bin/env python3
"""Generate opaque flat-only R74 LUTs from the ACTUAL R52 CRAM and R53 M50 partners."""
from pathlib import Path
import argparse,hashlib,json,re,runpy
import numpy as np
def array(s,n):
    m=re.search(r'\b'+re.escape(n)+r'\[\d+\]\s*=\s*\{([^}]+)\}',s,re.S)
    assert m,n
    return np.asarray([int(x,0) for x in re.findall(r'0x[0-9a-fA-F]+|\d+',m.group(1))],int)
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--profile',choices=['a','l'],required=True)
    p.add_argument('--policy',choices=['ctl','f1','f2','f3'],required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2];src=root/'src'
    palette_report=json.loads((src/'r52_ab_report.json').read_text())
    micro_report=json.loads((src/'r53_micro_report.json').read_text())
    expected_mode='near25' if a.profile=='a' else 'luma32'
    expected_zero='allow' if a.profile=='a' else 'forbid'
    assert palette_report['args']['mode']==expected_mode, (a.profile,'R52 wrong palette')
    assert palette_report['args']['zero_policy']==expected_zero, (a.profile,'R52 wrong zero policy')
    assert micro_report['ratio_percent']==50, 'R53 M50 companion ratio required'
    assert micro_report['zero_policy']==expected_zero, 'R53 companion source mismatch'
    gp=runpy.run_path(str(root/'scripts/genpal.py'))
    g=runpy.run_path(str(root/'scripts/lab/gen_r52_claudio.py'))
    h=(src/'r52_ab_tables.h').read_text();m=(src/'r53_micro_tables.h').read_text()
    pal=[array(h,'r52_pal'+str(k)).reshape(14,16) for k in range(2)]
    partner=[array(m,'r53_partner_'+k) for k in ('even','odd')]
    base=np.column_stack((array(h,'r52_even'),array(h,'r52_odd')))
    assert base.shape==(256,2) and all(len(x)==16 for x in partner)
    rgb=[np.asarray([[gp['gen_to_rgb'](int(v)) for v in row] for row in bank],float) for bank in pal]
    eff=[g['avg_rgb'](c,c[:,n]) for c,n in zip(rgb,partner)]
    target=np.asarray(gp['decode_subpal'](gp['load_playpal'](),0),float)
    lab=g['to_lab'](target)
    ij=np.array([(i,j) for i in range(1,16) for j in range(1,16)],int)
    ii,jj=ij.T
    mean=g['avg_rgb'](eff[0][0,ii],eff[1][0,jj])
    mlab=g['to_lab'](mean)
    contrast=g['delta_e'](eff[0][0,ii],eff[1][0,jj])
    dl=np.abs(g['luma'](eff[0][0,ii])-g['luma'](eff[1][0,jj]))
    grain=np.zeros(len(ij),float)
    for bank,indices in enumerate((ii,jj)):
        grain+=g['delta_e'](rgb[bank][0,indices],rgb[bank][0,partner[bank][indices]])*.5
    chosen=base.copy();rows=[]
    for c in range(256):
        old=g['avg_rgb'](eff[0][0,base[c,0]],eff[1][0,base[c,1]])
        baseline=float(g['delta_e'](old,target[c]))
        if a.policy=='ctl':continue
        err=np.linalg.norm(mlab-lab[c],axis=1)
        chrom=np.hypot(lab[c,1],lab[c,2]);cand=np.hypot(mlab[:,1],mlab[:,2])
        hue=np.zeros(len(ij),float)
        if chrom>15:
            hue+=np.maximum(0,chrom*.5-cand)*2
            cos=(mlab[:,1]*lab[c,1]+mlab[:,2]*lab[c,2])/np.maximum(1e-6,cand*chrom)
            hue+=chrom*np.maximum(0,.75-np.clip(cos,-1,1))
        lam,mu={'f1':(4,.5),'f2':(1.5,.2),'f3':(1.5,.2)}[a.policy]
        score=err+lam*contrast+mu*dl+.12*grain+hue
        valid=np.ones(len(ij),bool)
        if a.policy=='f2':valid &= err<=max(12,1.5*baseline)
        if a.policy=='f3':valid &= (contrast<=10)&(dl<=8)&(err<=max(4,1.25*baseline))
        fallback=False
        if not valid.any():
            fallback=True
            valid=err<=max(12,1.5*baseline)
            if not valid.any():valid[:]=True
        score[~valid]=np.inf
        k=int(np.lexsort((jj,ii,np.abs(ii-jj),score))[0]);chosen[c]=ij[k]
        rows.append(dict(c=c,pair=ij[k].tolist(),target_error=float(err[k]),between_columns=float(contrast[k]),luma_gap=float(dl[k]),baseline_error=baseline,fallback=fallback))
    lines=['/* R74 fixed flat-only LUTs (offline M50 effective color search) */','#ifndef R74_FLAT_TABLES_H','#define R74_FLAT_TABLES_H','#include <stdint.h>']
    for side,col in [('even',0),('odd',1)]:lines.append('static const uint8_t r74_flat_'+side+'[256]={'+','.join(map(str,chosen[:,col]))+'};')
    lines.append('#endif')
    dest=src/'r74_flat_tables.h';dest.write_text('\n'.join(lines)+'\n')
    report=dict(profile=a.profile,policy=a.policy,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),zero_count=int((chosen==0).any(axis=1).sum()),original_zero_count=int((base==0).any(axis=1).sum()),metric='CRAM-quantized linear-light M50 and CIELAB deltaE76',rows=rows)
    (src/'r74_flats_report.json').write_text(json.dumps(report,indent=2)+'\n')
    assert a.policy=='ctl' or not np.any(chosen==0)
    print('R74',a.profile,a.policy,'zero',report['zero_count'],report['sha256'],flush=True)
if __name__=='__main__':main()
