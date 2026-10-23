#!/usr/bin/env python3
"""R57 fixed-R55 palette colour-diversity experiments, offline generation.

Optimizes <=15 pair CODES per plane. Does not build a ROM or emulate a CRT.
Requires NumPy. Inputs are the pinned repository WAD and R55 snapshots.
"""
import argparse
import base64
import lzma
import runpy
import subprocess
import hashlib
import json
from pathlib import Path
import numpy as np


def linear(rgb):
    x = np.asarray(rgb, float) / 255.
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)


def encoded(rgb):
    x = np.clip(rgb, 0, 1)
    return np.where(x <= .0031308, 12.92*x, 1.055*x**(1/2.4)-.055)*255


def lab(rgb):
    matrix = np.array([[.4124,.3576,.1805],[.2126,.7152,.0722],[.0193,.1192,.9505]])
    xyz = (linear(rgb) @ matrix.T) / np.array([.95047,1.,1.08883])
    f = np.where(xyz > .008856, np.cbrt(xyz), 7.787*xyz+16/116)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],-1)


def cram_rgb(words):
    w = np.asarray(words, int)
    q = np.stack([(w >> 1)&7,(w >> 5)&7,(w >> 9)&7],-1)
    return ((q << 5)|(q << 2)|(q >> 1)).astype(float)


PAIRS = np.asarray([(a,b) for a in range(1,16) for b in range(a,16)], int)


def fit_cost(pal, target, profile):
    a = pal[:,PAIRS[:,0]]; b = pal[:,PAIRS[:,1]]
    mixed = encoded((linear(a)+linear(b))*.5)
    la,lb,lm,lt = lab(a),lab(b),lab(mixed),lab(target)
    effects = np.array([.75]+[.25/13]*13)
    error = np.sum((lt[:,:,None,:]-lm[:,None,:,:])**2,axis=-1)
    # Prefer saturation in the MIXTURE; do not boost every endpoint blindly.
    ct = np.linalg.norm(lt[...,1:],axis=-1)
    ca = np.linalg.norm(la[...,1:],axis=-1); cb = np.linalg.norm(lb[...,1:],axis=-1)
    cm = np.linalg.norm(lm[...,1:],axis=-1)
    undersat = np.maximum(0,ct[:,:,None]-cm[:,None,:])**2
    error += .75*undersat*(ct[:,:,None]>20)
    grain = np.sum((la-lb)**2,axis=-1)
    error += .025*grain[:,None,:]
    # Discourage opposing hues. Near-neutral endpoints do not have a stable hue.
    for endpoint,chroma in ((la,ca),(lb,cb)):
        cosine = np.sum(lt[:,:,None,1:]*endpoint[:,None,:,1:],axis=-1)
        cosine /= np.maximum(1e-6,ct[:,:,None]*chroma[:,None,:])
        hue = np.maximum(0,.75-cosine)**2 * ct[:,:,None]**2
        valid = (ct[:,:,None]>20)&(chroma[:,None,:]>12)
        error += (.45 if profile=='H1' else .20)*hue*valid
    dl = np.abs(la[...,0]-lb[...,0])
    error += .12*np.maximum(0,dl[:,None,:]-12)**2
    cost = np.sum(effects[:,None,None]*error,axis=0)/10000.
    legal = (np.max(dl,axis=0)<=30)&(np.max(np.sqrt(grain),axis=0)<=50)
    if profile=='H2':
        # Neutral-secondary comparison: all solids allowed; mixed pairs require
        # a near-neutral normal-palette endpoint. No compulsory gray mixing.
        legal &= (PAIRS[:,0]==PAIRS[:,1])|(np.minimum(ca[0],cb[0])<=14)
    cost[:,~legal] += 1000.
    return cost,lm,effects


def optimize(snapshot, target, weights, count, profile, ab_tolerance=0., accent_reserve=False):
    palettes = [cram_rgb(np.asarray(snapshot['r52_pal'+str(i)]).reshape(14,16)) for i in range(2)]
    features=[fit_cost(pal,target,profile) for pal in palettes]
    cost=[item[0] for item in features]
    coarse=np.sum(features[0][2][:,None,None]*np.sum(
        (features[0][1][:,:,None,:]-features[1][1][:,None,:,:])**2,axis=-1),axis=0)/10000.
    coarse=np.maximum(0.,np.sqrt(coarse)-ab_tolerance/100.)**2
    anchors=[int(np.flatnonzero((PAIRS==[i,i]).all(axis=1))[0]) for i in range(1,count+1)]
    books=[]
    locked_counts=[]
    for plane in range(2):
        book=anchors.copy()
        if accent_reserve:
            tl=lab(target[0]); tc=np.linalg.norm(tl[:,1:],axis=1)
            th=np.degrees(np.arctan2(tl[:,2],tl[:,1]))%360
            ml=features[plane][1][0]; mc=np.linalg.norm(ml[:,1:],axis=1)
            mh=np.degrees(np.arctan2(ml[:,2],ml[:,1]))%360
            for center in (40.,140.):  # one red and one green code per plane
                angle=lambda h: np.abs((h-center+180)%360-180)
                mask=(tc>20)&(angle(th)<35)&(weights>0)
                if not mask.any():raise ValueError('missing accent family in training weights')
                losses=np.sum(weights[mask,None]*cost[plane][mask],axis=0)/weights[mask].sum()
                losses[(mc<15)|(angle(mh)>35)]=np.inf
                losses[book]=np.inf
                choice=int(np.argmin(losses))
                if not np.isfinite(losses[choice]):raise ValueError('palette cannot reserve requested accent')
                book.append(choice)
        locked_counts.append(len(book))
        while len(book)<15:
            best=cost[plane][:,book].min(axis=1)
            losses=np.sum(weights[:,None]*np.minimum(best[:,None],cost[plane]),axis=0)
            losses[book]=np.inf
            book.append(int(np.argmin(losses)))
        books.append(np.asarray(book,int))

    def assign():
        scores=(cost[0][:,books[0]][:,:,None]+cost[1][:,books[1]][:,None,:]
                +.35*coarse[np.ix_(books[0],books[1])][None,:,:])
        flat=scores.reshape(256,-1); winner=flat.argmin(axis=1)
        return [winner//15,winner%15],float(np.dot(weights,flat[np.arange(256),winner]))

    maps,objective=assign(); history=[objective]
    for _ in range(8):
        previous=objective
        for plane in range(2):
            for slot in range(locked_counts[plane],15):
                owned=np.flatnonzero(maps[plane]==slot)
                if not len(owned):continue
                other=books[1-plane][maps[1-plane][owned]]
                cross=coarse[:,other].T if plane==0 else coarse[other,:]
                losses=np.sum(weights[owned,None]*(cost[plane][owned,:]+.35*cross),axis=0)
                forbidden=[p for k,p in enumerate(books[plane]) if k!=slot]
                losses[forbidden]=np.inf
                books[plane][slot]=int(np.argmin(losses))
            maps,objective=assign()
            assert objective<=history[-1]+1e-10,'non-monotonic coordinate descent'
            history.append(objective)
        if previous-objective<1e-10:break
    codebooks=[np.vstack([[0,0],PAIRS[book]]).astype(int) for book in books]
    maps=[m+1 for m in maps]
    # Pair IDs are NOT CRAM indices. Slot 1..N are still anchor (i,i).
    for book in codebooks:
        assert book.shape==(16,2) and np.array_equal(book[1:count+1],[[i,i] for i in range(1,count+1)])
        assert (book[1:]>=1).all() and (book[1:]<=15).all()
    flat=np.asarray(snapshot['r55_flat_even'],int)
    assert len(flat)==256 and (flat>=1).all() and (flat<=count).all()
    for sp in range(14):
        assert np.array_equal(palettes[0][sp,flat],palettes[1][sp,flat])
    metrics=[]
    for sp in range(14):
        emitted=[]
        for plane in range(2):
            colors=palettes[plane][sp,codebooks[plane][maps[plane]]]
            emitted.append(encoded(linear(colors).mean(axis=1)))
        err=[np.linalg.norm(lab(c)-lab(target[sp]),axis=1) for c in emitted]
        seam=np.linalg.norm(lab(emitted[0])-lab(emitted[1]),axis=1)
        metrics.append({'sub':sp,'weighted_pair_mean_dE':float(np.dot(weights,(err[0]+err[1])*.5)),
                        'same_target_A_B_dE':float(np.dot(weights,seam))})
    return {'profile':profile,'anchors':count,'ab_tolerance':ab_tolerance,'reserved_accent_codes':locked_counts[0]-count,'codebooks':[b.tolist() for b in codebooks],
            'wall_maps':[m.tolist() for m in maps],'objective_history':history,
            'per_subpalette':metrics,'notes':['Fixed CRAM, pair-code selection only. No palette reoptimization.',
            'Proxy-trained metrics, not measured CRT fidelity, gameplay or frame time.',
            'Four-pixel phase differences remain possible on walls; flats use identical solid anchors.']}


PROFILES = {
    'c55-a6': {'control':'r55', 'anchors':6},
    'c56-a6': {'control':'r56', 'anchors':6},
    'a6-fixed': {'anchors':6, 'balanced':0., 'tolerance':0., 'accents':False},
    'a6-balanced': {'anchors':6, 'balanced':.5, 'tolerance':0., 'accents':False},
    'a6-tolerant': {'anchors':6, 'balanced':.5, 'tolerance':8., 'accents':False},
    'a6-accents': {'anchors':6, 'balanced':.5, 'tolerance':8., 'accents':True},
    'a4-tolerant': {'anchors':4, 'balanced':.5, 'tolerance':8., 'accents':False},
    'a4-accents': {'anchors':4, 'balanced':.5, 'tolerance':8., 'accents':True},
}


def balanced_weights(target, frequency, share):
    """Mix frequency with equal mass per NONEMPTY hue/light bin.

    Seven hue sectors plus neutral (C*<20), three L* levels. Relative
    frequencies inside each bin are preserved; empty bins get no weight.
    """
    lt=lab(target);chroma=np.linalg.norm(lt[:,1:],axis=1)
    hue=np.degrees(np.arctan2(lt[:,2],lt[:,1]))%360
    family=np.where(chroma<20,7,(hue/360*7).astype(int))
    light=np.digitize(lt[:,0],[25,50]);bins=family*3+light
    equal=np.zeros(256)
    active=[b for b in np.unique(bins) if frequency[bins==b].sum()>0]
    for b in active:
        mask=bins==b;equal[mask]=frequency[mask]/frequency[mask].sum()/len(active)
    result=(1-share)*frequency+share*equal
    assert np.isfinite(result).all() and abs(result.sum()-1)<1e-8
    return result, {'equal_bin_share':share,'nonempty_bins':len(active),
                    'dark_mass_L25':float(result[lt[:,0]<25].sum()),
                    'chromatic_mass_C20':float(result[chroma>=20].sum())}


def emit_array(name,values,typ='uint8_t'):
    a=np.asarray(values);dims=''.join('['+str(n)+']' for n in a.shape)
    if a.ndim==1:body=','.join(map(str,a.tolist()))
    else:body=',\n'.join('{'+','.join(map(str,row.tolist()))+'}' for row in a)
    return 'static const '+typ+' '+name+dims+'={\n'+body+'\n};'


def export_header(snapshot,result,colormap):
    cm=np.asarray(colormap).reshape(34,256)
    lines=['/* R57 generated offline. Pair code != CRAM index. */',
           '#ifndef R56_TABLES_H','#define R56_TABLES_H','#include <stdint.h>',
           '#define R56_ANCHORS '+str(result['anchors'])]
    for plane,side in enumerate(('even','odd')):
        lines.append(emit_array('r56_pal'+str(plane),np.asarray(snapshot['r52_pal'+str(plane)]).reshape(14,16),'uint16_t'))
        lines.append(emit_array('r56_pairs_'+side,result['codebooks'][plane]))
        lines.append(emit_array('r56_wall_'+side,result['wall_maps'][plane]))
        lines.append(emit_array('r56_comp_'+side,np.asarray(result['wall_maps'][plane])[cm]))
        lines.append(emit_array('r56_flat_'+side,snapshot['r55_flat_even']))
    lines.append('#endif\n');return '\n'.join(lines)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',default='.')
    ap.add_argument('--out',default='dist/r57-diversity/tables')
    args=ap.parse_args();repo=Path(args.repo).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    g=runpy.run_path(str(repo/'scripts/lab/gen_r52_claudio.py'))
    gp=runpy.run_path(str(repo/'scripts/genpal.py'))
    wad=(repo/'scripts/doom64.wad').read_bytes();lumps=g['wad_lumps'](wad)
    cm=np.frombuffer(next(d for n,d in lumps if n=='COLORMAP'),dtype=np.uint8)
    assert len(cm)==34*256
    source=gp['load_playpal']();target=np.array([gp['decode_subpal'](source,s) for s in range(14)],float)
    freq=g['proxy_histogram'](lumps,1.,range(6,23),.35,cm)
    frozen=runpy.run_path(str(repo/'scripts/lab/r55_werk_snapshot.py'))['SNAPSHOTS']
    snapshots={key:json.loads(lzma.decompress(base64.b64decode(value))) for key,value in frozen.items()}
    report={'generator':'gen_r57_diversity.py','base_commit':'a64758c342e4f5565b9dbc06bb0db1daca19044f',
            'weights':'wall-patch proxy, COLORMAP6..22,35% uniform; not rendered screen counts',
            'models':'CIELAB76/linear-sRGB pair mean; no calibrated CRT model',
            'wad_sha256':hashlib.sha256(wad).hexdigest(),'profiles':{}}
    for name,config in PROFILES.items():
        snapshot=snapshots['a'+str(config['anchors'])]
        if config.get('control')=='r56':
            subprocess.run(['python3',str(repo/'scripts/lab/r56_claudio_snapshot.py'),'--out',str(out/(name+'.h'))],check=True)
            result={'control':'byte-exact R56 snapshot','anchors':6}
        else:
            weights,stats=balanced_weights(target[0],freq,config.get('balanced',0.))
            if config.get('control')=='r55':
                result={'anchors':6,'codebooks':[[[i,i] for i in range(16)] for _ in range(2)],
                        'wall_maps':[snapshot['r52_even'],snapshot['r52_odd']],
                        'control':'R55 A6 palettes/maps, degenerate pairs; identical pixel colours'}
            else:
                result=optimize(snapshot,target,weights,config['anchors'],'H1',config['tolerance'],config['accents'])
            header=export_header(snapshot,result,cm);(out/(name+'.h')).write_text(header)
            result['weight_bins']=stats
        result['config']=config
        result['header_sha256']=hashlib.sha256((out/(name+'.h')).read_bytes()).hexdigest()
        report['profiles'][name]=result
        print('R57',name,'ready',result['header_sha256'][:12],flush=True)
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()

