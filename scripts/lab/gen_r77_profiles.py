#!/usr/bin/env python3
"""R77 blue-anchor Hybrid CRAM and offline normal/shadow candidate report.
No highlight. MiSTer VDP DAC input model N(c)=2*c, S(c)=c (c=0..7).
RGB/Lab averages are an uncalibrated linear-DAC/sRGB proxy, not TV measures.
"""
from pathlib import Path
import csv,hashlib,itertools,json,re,runpy
import numpy as np

ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'src'
aux=runpy.run_path(str(ROOT/'scripts/lab/gen_r74_flats.py'));array=aux['array']
math=runpy.run_path(str(ROOT/'scripts/lab/gen_r52_claudio.py'))
gp=runpy.run_path(str(ROOT/'scripts/genpal.py'))
avg=math['avg_rgb'];lab=math['to_lab'];de=math['delta_e']
header=(SRC/'r59_color_tables.h').read_text()
def parse(name):
    m=re.search(r'\b'+name+r'(?:\[\d+\])+\s*=\s*\{(.*?)\};',header,re.S)
    assert m,name
    return np.array([int(v,0) for v in re.findall(r'0x[\da-fA-F]+|\d+',m[1])],int)
def profile(tag,flat):
    return dict(pal=[parse('r76_'+tag+'_pal'+str(b)).reshape(14,16) for b in (0,1)],
        partner=[parse('r76_'+tag+'_pairs_'+s).reshape(16,2)[:,1] for s in ('even','odd')],
        wall=[parse('r76_'+tag+'_wall_'+s) for s in ('even','odd')],
        flat=[parse('r76_'+flat+'_flat_'+s) for s in ('even','odd')])
def rgb(p,shadow=False):
    # CRAM component c -> DAC input 2*c (normal) / c (shadow), normalized by 14.
    return [np.stack([((bank>>1)&7),((bank>>5)&7),((bank>>9)&7)],axis=-1)*(255.0/(14 if shadow else 7)) for bank in p['pal']]
def effective(p,shadow=False):
    return [avg(c,c[:,n]) for c,n in zip(rgb(p,shadow),p['partner'])]
def flatcolors(p):
    e=effective(p)
    return avg(e[0][:,p['flat'][0]],e[1][:,p['flat'][1]])
A=profile('a','a');L=profile('l','l');HN=profile('l','n');OLD=profile('l','b')
source=np.asarray([gp['decode_subpal'](gp['load_playpal'](),p) for p in range(14)],float)
source_blue=(source[0,:,2]>source[0,:,0]*1.18)&(source[0,:,2]>source[0,:,1]*1.12)&(source[0,:,2]>42)&((source[0,:,2]-source[0,:,0])>19)
target=flatcolors(A)
# Ignore source blues that A2 itself renders neutral. Keep those HN-like.
blue=source_blue & (target[0,:,2]>target[0,:,0]*1.5+8) & (target[0,:,2]>target[0,:,1]*1.5+8)
# A2's three blue M50 means use neighbouring 3-bit blue levels (1,2),(2,3),(3,4).
# Share the four raw levels across PAL0/PAL1; each column uses the same fine mix.
anchor_words=np.array([0x200,0x400,0x600,0x800],int)
anchor_rgb=np.array([[0.,0.,k*255./7.] for k in range(1,5)])
anchor_src=[]
for word,color in zip(anchor_words,anchor_rgb):
    matches=[c for c in range(256) if int(gp['gen_color'](source[0,c].astype(int)))==int(word)]
    assert matches,word
    anchor_src.append(min(matches,key=lambda c:float(de(source[0,c],color))))
anchors=np.array([[int(w) if p==0 else int(gp['gen_color'](source[p,c].astype(int))) for w,c in zip(anchor_words,anchor_src)] for p in range(14)])
H={k:[v.copy() for v in vs] for k,vs in L.items()}
old_effective=effective(L);slot_reports=[]
palette_report=json.loads((SRC/'r52_ab_report.json').read_text())
lumps=math['wad_lumps']((ROOT/'scripts/doom64.wad').read_bytes())
rawcm=next(v for n,v in lumps if n=='COLORMAP')
weights=math['proxy_histogram'](lumps,.7,range(6,23),.35,np.frombuffer(rawcm,dtype=np.uint8))
weights=np.asarray(weights,float)
assert weights.shape==(256,)
for b in (0,1):
    winner=None
    existing={k:int(np.flatnonzero(L['pal'][b][0]==word)[0]) for k,word in enumerate(anchor_words) if np.any(L['pal'][b][0]==word)}
    missing=[k for k in range(4) if k not in existing]
    free=[i for i in range(1,16) if i not in existing.values()]
    for replacement in itertools.permutations(free,len(missing)):
        assigned=dict(existing);assigned.update(zip(missing,replacement))
        slots=tuple(assigned[k] for k in range(4))
        pal=H['pal'][b].copy();partner=L['partner'][b].copy()
        for k,slot in enumerate(slots):
            pal[:,slot]=anchors[:,k];partner[slot]=slots[min(k+1,3)]
        raw=np.asarray([[gp['gen_to_rgb'](int(w)) for w in row] for row in pal],float)
        for i in range(1,16):
            if i not in slots and int(partner[i]) in slots:
                options=[j for j in range(1,16) if j not in slots]
                mix=avg(raw[0,i],raw[0,options])
                partner[i]=options[int(np.argmin(de(mix,old_effective[b][0,i])))]
        eff=avg(raw,raw[:,partner])
        errors=de(eff[0,None,1:],old_effective[b][0,L['wall'][b],None])
        remap=np.argmin(errors,axis=1)+1
        loss=float((errors[np.arange(256),remap-1]*weights).sum())
        key=(loss,slots)
        if winner is None or key<winner[0]:winner=(key,pal,partner,remap,eff)
    (loss,slots),pal,partner,remap,eff=winner
    H['pal'][b]=pal;H['partner'][b]=partner;H['wall'][b]=remap
    slot_reports.append(dict(bank=b,slots=list(slots),weighted_deltaE_from_L3=loss,
        changed_wall_indices=int(np.sum(remap!=L['wall'][b]))))
e=effective(H);hncolors=flatcolors(HN);ij=np.array(list(itertools.product(range(1,16),repeat=2)));ii,jj=ij.T
mix=avg(e[0][0,ii],e[1][0,jj]);mixlab=lab(mix);contrast=de(e[0][0,ii],e[1][0,jj])
lumagap=np.abs(math['luma'](e[0][0,ii])-math['luma'](e[1][0,jj]))
maps=np.empty((256,2),int)
for c in range(256):
    if blue[c]:
        k=int(np.argmin(de(e[0][0,slot_reports[0]['slots']],target[0,c])))
        maps[c]=[slot_reports[b]['slots'][k] for b in (0,1)]
    else:
        errors=de(mix,hncolors[0,c]);t=lab(hncolors[0,c]);chroma=np.linalg.norm(t[1:]);cc=np.linalg.norm(mixlab[:,1:],axis=1)
        hue=np.zeros(225)
        if chroma>14:
            cosine=np.sum(mixlab[:,1:]*t[1:],axis=1)/np.maximum(1e-6,cc*chroma)
            hue=chroma*np.maximum(0,.7-np.clip(cosine,-1,1))+2*np.maximum(0,.45*chroma-cc)
        score=errors+.3*de(mix,source[0,c])+2.8*contrast+.4*lumagap+hue
        valid=errors<=max(18,1.8*float(errors.min()));score[~valid]=np.inf
        maps[c]=ij[int(np.argmin(score))]
H['flat']=[maps[:,0],maps[:,1]]
def emit(name,values,typ='uint8_t',row=None):
    v=np.asarray(values).flatten().tolist()
    dims='['+str(len(v))+']' if row is None else '['+str(len(v)//row)+']['+str(row)+']'
    values=','.join(map(str,v)) if row is None else ',\n'.join('{'+','.join(map(str,v[k:k+row]))+'}' for k in range(0,len(v),row))
    return 'static const '+typ+' '+name+dims+'={'+values+'};\n'
cm=math['wad_lumps']((ROOT/'scripts/doom64.wad').read_bytes())
cm=np.frombuffer(next(v for n,v in cm if n=='COLORMAP'),dtype=np.uint8).reshape(-1,256)
generated=[]
for b,side in enumerate(('even','odd')):
    generated.extend([emit('r77_h_pal'+str(b),H['pal'][b],'uint16_t',16),
      emit('r77_h_pairs_'+side,np.column_stack((np.arange(16),H['partner'][b])),row=2),
      emit('r77_h_wall_'+side,H['wall'][b]),emit('r77_h_flat_'+side,H['flat'][b]),
      emit('r77_h_comp_'+side,H['wall'][b][cm],row=256)])
needle='static const R59ColorTables r59_color_tables[R59_COLOR_MODES]={'
assert header.count(needle)==1
header=header.replace(needle,''.join(generated)+needle)
old='{r76_l_pal0,r76_l_pal1,r76_l_pairs_even,r76_l_pairs_odd,r76_l_wall_even,r76_l_wall_odd,r76_b_flat_even,r76_b_flat_odd,r76_l_comp_even,r76_l_comp_odd}'
new='{r77_h_pal0,r77_h_pal1,r77_h_pairs_even,r77_h_pairs_odd,r77_h_wall_even,r77_h_wall_odd,r77_h_flat_even,r77_h_flat_odd,r77_h_comp_even,r77_h_comp_odd}'
assert header.count(old)==1;header=header.replace(old,new)
(SRC/'r59_color_tables.h').write_text(header)
final_colors=flatcolors(H);old_colors=flatcolors(OLD)
report=dict(blue_source_indices=np.flatnonzero(blue).tolist(),anchor_words=[int(w) for w in anchor_words],
    anchor_rgb=anchor_rgb.tolist(),anchor_source_indices=anchor_src,slot_changes=slot_reports,
    source='Hybrid CRAM modified; A2/L3/HN generated arrays preserved. Normal mode gameplay, no shadow in renderer yet.',
    generated_sha256=hashlib.sha256(header.encode()).hexdigest(),
    blue_mean_deltaE_to_A2_before=float(de(old_colors[0,blue],target[0,blue]).mean()),
    blue_mean_deltaE_to_A2_after=float(de(final_colors[0,blue],target[0,blue]).mean()),
    blue_max_between_columns_after=float(de(e[0][0,maps[blue,0]],e[1][0,maps[blue,1]]).max()),
    playpal_blue_error=[float(de(final_colors[p,blue],target[p,blue]).mean()) for p in range(14)],
    model='CIELAB76, linear-light M50, linearized DAC proxy; not measured TV colors')
(SRC/'r77_profiles_report.json').write_text(json.dumps(report,indent=2)+'\n')

# Enumerate all opaque code pairs for the four requested profiles, no highlight.
profiles={'Hybrid Blue+':H,'A2 Full':A,'L3 Detail':L,'HN Smooth':HN}
shadow_report=dict(core='MiSTer-devel/Genesis_MiSTer rtl/vdp.vhd',
    core_commit='adc0c42cfb1fa5d484cc8566767f7d68982bc44a',dac_rule='normal = 2*c, shadow = c; c in 0..7',
    model=report['model'],highlight=False,
    full_cram_normal_rgb=512,full_cram_shadow_rgb=512,full_cram_union_rgb=960,
    channel_union_levels=sorted(set(range(0,15,2))|set(range(8))),
    geometry='NN and SS are uniform-region candidates. NS/SN are theoretical independent masks; not freely selectable per 4px column in current Pair-V.',profiles={})
pair_rows=[];blue_rows=[]
for name,p in profiles.items():
    eff={'N':effective(p),'S':effective(p,True)};counts={};allkeys=set();uniform=set()
    for mode in ('NN','SS','NS','SN'):
        a=eff[mode[0]][0][0,ii];b=eff[mode[1]][1][0,jj];m=avg(a,b)
        keys={tuple(v) for v in np.round(m,6)};counts[mode]=len(keys);allkeys|=keys
        if mode in ('NN','SS'):uniform|=keys
        for k,(i,j) in enumerate(ij):
            pair_rows.append([name,mode,int(i),int(j),*m[k].tolist(),float(de(a[k],b[k])),mode in ('NN','SS')])
        for c in np.flatnonzero(blue):
            error=de(m,target[0,c]);gap=de(a,b);best=int(np.argmin(error+1.5*gap))
            blue_rows.append([name,int(c),mode,int(ii[best]),int(jj[best]),float(error[best]),float(gap[best]),mode in ('NN','SS')])
    base={tuple(v) for v in np.round(avg(eff['N'][0][0,ii],eff['N'][1][0,jj]),6)}
    rawN={tuple(((int(w)>>1)&7,(int(w)>>5)&7,(int(w)>>9)&7)[k]*2 for k in range(3)) for pal in p['pal'] for w in pal[0,1:]}
    rawS={tuple(((int(w)>>1)&7,(int(w)>>5)&7,(int(w)>>9)&7)[k] for k in range(3)) for pal in p['pal'] for w in pal[0,1:]}
    shadow_report['profiles'][name]=dict(candidate_pairs_per_mode=225,unique_m50_mean_by_mode=counts,
       uniform_region_unique_means=len(uniform),new_uniform_means_over_NN=len(uniform-base),
       ideal_independent_unique_means=len(allkeys),ideal_extra_over_NN=len(allkeys-base),
       raw_normal_unique=len(rawN),raw_normal_shadow_union=len(rawN|rawS))
with (SRC/'r77_shadow_pairs.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['profile','mode','even_code','odd_code','mean_R','mean_G','mean_B','between_deltaE76','uniform_region_candidate']);w.writerows(pair_rows)
with (SRC/'r77_blue_comparison.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['profile','source_c','mode','even_code','odd_code','target_A2_error_deltaE76','between_deltaE76','uniform_region_candidate']);w.writerows(blue_rows)
(SRC/'r77_shadow_report.json').write_text(json.dumps(shadow_report,indent=2)+'\n')
print('R77 Hybrid Blue anchors/report',json.dumps(report),flush=True)
print('R77 normal/shadow candidates',json.dumps(shadow_report['profiles']),flush=True)
