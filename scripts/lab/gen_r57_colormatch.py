#!/usr/bin/env python3
"""R57 ColorMatch: offline Pair-V hue-balanced alternative to R56 A6M.

No gameplay or runtime rendering changes. Preserve six shared flat anchors;
use the 8x8 four-CRAM reference as a color *target*, reserve palette capacity
across rare hue families, cap the dark proxy, and relax plane agreement only
for chromatic wall targets. Deterministic experiment, not a calibrated CRT.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import runpy
import struct
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
M=np.array([[.4124,.3576,.1805],[.2126,.7152,.0722],[.0193,.1192,.9505]])
WHITE=np.array([.95047,1.,1.08883])
FAMILIES=("red","orange","yellow","green","blue","purple")

def linear(rgb):
    x=np.asarray(rgb,float)/255.
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)

def encoded(x):
    x=np.clip(x,0,1)
    return np.where(x<=.0031308,12.92*x,1.055*x**(1/2.4)-.055)*255.

def lab(rgb):
    xyz=linear(rgb)@M.T/WHITE
    f=np.where(xyz>.008856,np.cbrt(xyz),7.787*xyz+16/116)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],axis=-1)

def color_family(l):
    l=np.asarray(l)
    c=np.linalg.norm(l[...,1:],axis=-1)
    h=(np.degrees(np.arctan2(l[...,2],l[...,1]))+360.)%360.
    bins=np.select([((h<25)|(h>=345)),(h>=25)&(h<70),
                    (h>=70)&(h<105),(h>=105)&(h<195),
                    (h>=195)&(h<315),(h>=315)&(h<345)],
                   [1,2,3,4,5,6],default=0)
    return np.where((c>=17)&(l[...,0]>=13),bins,0).astype(int)

def carray(text,name,shape):
    match=re.search(r"\b"+re.escape(name)+r"((?:\[\d+\])+)[ \t]*=[ \t]*\{(.*?)\};",text,re.S)
    if match is None:raise ValueError("array missing: "+name)
    dims=tuple(int(n) for n in re.findall(r"\[(\d+)\]",match.group(1)))
    assert dims==tuple(shape),(name,dims,shape)
    values=[int(n) for n in re.findall(r"\d+",match.group(2))]
    assert len(values)==int(np.prod(shape)),(name,len(values),shape)
    return np.asarray(values,dtype=int).reshape(shape)

def read_colormap(path):
    data=path.read_bytes()
    assert data[:4]==b"IWAD"
    n=struct.unpack_from(">h",data,4)[0]
    off=struct.unpack_from(">I",data,8)[0]
    for i in range(n):
        p=off+16*i
        if data[p+8:p+16].split(b"\0")[0]==b"COLORMAP":
            start=struct.unpack_from(">I",data,p)[0]
            length=struct.unpack_from(">H",data,p+4)[0]
            assert length==34*256
            return np.frombuffer(data[start:start+length],dtype=np.uint8).reshape(34,256)
    raise ValueError("COLORMAP missing")

def emit(name,a,dtype):
    a=np.asarray(a,dtype=int)
    dims="".join(f"[{n}]" for n in a.shape)
    vals=a.ravel().tolist()
    rows=[",".join(map(str,vals[i:i+24])) for i in range(0,len(vals),24)]
    return f"static const {dtype} {name}{dims}={{\n"+",\n".join(rows)+"\n};\n"

def weights_for(target,cm):
    target_lab=lab(target)
    groups=color_family(target_lab)
    # Wall proxy is the COLORMAP histogram, not an observed DEMO3 frame.
    w=.25+np.bincount(cm[6:23].ravel(),minlength=256).astype(float)
    w/=w.sum()
    dark=target_lab[:,0]<25
    share=w[dark].sum()
    if share>.35:w[dark]*=(.35/(1-.35))*((1-share)/share)
    # Chromatic families are guaranteed a meaningful fraction of the objective.
    chroma=groups>0
    share=w[chroma].sum()
    if 0<share<.47:w[chroma]*=(.47/(1-.47))*((1-share)/share)
    # Prevent a single dark/post-COLORMAP target from monopolizing a code.
    positive=w[w>0]
    w=np.minimum(w,float(np.quantile(positive,.95))*1.5)
    return w/w.sum(),groups,target_lab

def reference_8x8(refpal,target_lab,gen):
    # The 8x8 mode can choose any of 4 palette banks per cell and a 50/50 pair
    # from each bank. This is a target model, NOT Pair-V palette switching.
    candidates=[]
    for bank in range(4):
        rgb=np.asarray([gen["gen_to_rgb"](w) for w in refpal[0,bank*16:bank*16+15]])
        for a in range(15):
            for b in range(a,15):
                candidates.append(encoded((linear(rgb[a])+linear(rgb[b]))/2))
    cols=np.asarray(candidates)
    cl=lab(cols)
    delta=((target_lab[:,None,:]-cl[None,:,:])**2).sum(-1)
    return cols[np.argmin(delta,axis=1)]

def pick_palette(base,refpal,gen,targets,w,groups,plane,prior):
    # 56 palette colors used by actual 8x8 graphics, with all 14 PLAYPAL
    # variants kept together per candidate source slot.
    src=[s for s in range(56)]
    cand=np.asarray([[refpal[k,(s//14)*16+1+(s%14)] for s in src]
                    for k in range(14)],dtype=int)
    normal=np.asarray([gen["gen_to_rgb"](v) for v in cand[0]],float)
    cl=lab(normal)
    cf=color_family(cl)
    taken=[]
    pal=base.copy()
    existing=np.asarray([gen["gen_to_rgb"](x) for x in pal[0,:7]],float)
    nearest=((lab(targets)[:,None,:]-lab(existing)[None,:,:])**2).sum(-1).min(axis=1)
    for fam in range(1,7):
        mask=groups==fam
        candidates=[i for i in range(56)
                    if cf[i]==fam and i not in taken
                    and (prior is None or i not in prior["slots"])]
        if not candidates or not mask.any():continue
        best=None
        for i in candidates:
            loss=((lab(targets[mask])-cl[i])**2).sum(axis=1)
            improvement=float(np.dot(w[mask],np.maximum(0,nearest[mask]-loss)))
            diversity=0.
            if prior is not None:
                # A mild preference for distinct A/B colors, not a forced
                # rainbow or an arbitrary difference between their outputs.
                delta=np.sqrt(((lab(prior["rgb"])-cl[i])**2).sum(axis=-1)).min()
                diversity=min(30.,float(delta))*.002
            score=improvement+diversity
            if best is None or score>best[0]:best=(score,i)
        assert best is not None
        taken.append(best[1])
        nearest=np.minimum(nearest,((lab(targets)-cl[best[1]])**2).sum(-1))
    while len(taken)<9:
        scores=[]
        for i in range(56):
            if i in taken or (prior is not None and i in prior["slots"]):continue
            d=((lab(targets)-cl[i])**2).sum(-1)
            gain=np.dot(w,np.maximum(0,nearest-d))
            bonus=0
            if prior is not None:
                delta=np.sqrt(((lab(prior["rgb"])-cl[i])**2).sum(axis=-1)).min()
                bonus=min(30.,float(delta))*.002
            scores.append((float(gain)+bonus,i))
        _,chosen=max(scores,key=lambda q:(q[0],-q[1]))
        taken.append(chosen)
        nearest=np.minimum(nearest,((lab(targets)-cl[chosen])**2).sum(-1))
    assert len(set(taken))==9
    for slot,i in enumerate(taken,7):
        pal[:,slot]=cand[:,i]
    return pal,taken

def pick_pairs(pal,targets,ref_targets,weights,groups,k=6):
    normal=lab(np.asarray([[((v>>1)&7)*255/7,
                            ((v>>5)&7)*255/7,
                            ((v>>9)&7)*255/7] for v in pal[0]],float))
    allpairs=np.array([(a,b) for a in range(1,16) for b in range(a,16)],int)
    rgb=np.asarray([[((v>>1)&7)*255/7,
                     ((v>>5)&7)*255/7,
                     ((v>>9)&7)*255/7] for v in pal[0]],float)
    mixed=encoded((linear(rgb[allpairs[:,0]])+linear(rgb[allpairs[:,1]]))/2)
    mixlab=lab(mixed)
    orig=lab(targets); ref=lab(ref_targets)
    loss=.8*((orig[:,None,:]-mixlab[None,:,:])**2).sum(-1)
    loss+=.2*((ref[:,None,:]-mixlab[None,:,:])**2).sum(-1)
    # High-contrast pair noise is costly; do not confuse codebook diversity
    # with an obligation to use exaggerated spatial dithering.
    components=np.sqrt(((normal[allpairs[:,0]]-normal[allpairs[:,1]])**2).sum(-1))
    loss+=.035*(components[None,:]**2)
    loss[:,components>55]+=5e5
    anchors=[int(np.flatnonzero(np.all(allpairs==[i,i],axis=1))[0]) for i in range(1,k+1)]
    book=anchors.copy()
    current=loss[:,book].min(axis=1)
    # Reserve at least one usable pair for each family; do not spend the
    # entire codebook on low-L* neutrals.
    for fam in range(1,7):
        mask=groups==fam
        if not mask.any() or len(book)>=15:continue
        candidates=[p for p in range(len(allpairs))
                    if p not in book and color_family(mixlab[p:p+1])[0]==fam
                    and components[p]<=55]
        if not candidates:continue
        score=np.asarray([np.dot(weights[mask],
                  np.maximum(0,current[mask]-loss[mask,p])) for p in candidates])
        selected=candidates[int(score.argmax())]
        book.append(selected)
        current=np.minimum(current,loss[:,selected])
    while len(book)<15:
        possibilities=[i for i in range(len(allpairs)) if i not in book]
        gain=[np.dot(weights,np.maximum(0,current-loss[:,i])) for i in possibilities]
        choice=possibilities[int(np.argmax(gain))]
        book.append(choice);current=np.minimum(current,loss[:,choice])
    codes=np.vstack([[0,0],allpairs[book]])
    return codes,loss[:,book],mixlab[book]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--header",default="src/r56_tables.h")
    ap.add_argument("--out",default="src/r56_tables.h")
    ap.add_argument("--report",default="src/r57_colormatch_report.json")
    args=ap.parse_args()
    gen=runpy.run_path(str(ROOT/"scripts/genpal.py"))
    gen["main"]()
    baseline=Path(args.header).read_text()
    pal0=carray(baseline,"r56_pal0",(14,16))
    pal1=carray(baseline,"r56_pal1",(14,16))
    flat=[carray(baseline,"r56_flat_even",(256,)),carray(baseline,"r56_flat_odd",(256,))]
    assert np.array_equal(flat[0],flat[1])
    assert np.all((flat[0]>=1)&(flat[0]<=6))
    assert np.array_equal(pal0[:,:7],pal1[:,:7]),"flat palette anchors differ"
    refheader=(ROOT/"src/gen_pal.h").read_text()
    refmatch=re.search(r"genpal_cram\[GENPAL_NSUB\]\[64\]\s*=\s*\{(.*?)\};",refheader,re.S)
    assert refmatch,"8x8 CRAM missing"
    rows=re.findall(r"\{([^{}]+)\}",refmatch.group(1))
    refpal=np.array([[int(s,16) for s in re.findall(r"0x[0-9a-fA-F]+",row)] for row in rows],int)
    assert refpal.shape==(14,64),refpal.shape
    pp=gen["load_playpal"]()
    target=np.asarray(gen["decode_subpal"](pp,0),float)
    cm=read_colormap(ROOT/"scripts/doom64.wad")
    w,groups,tl=weights_for(target,cm)
    eight=reference_8x8(refpal,tl,gen)
    palettes=[];selections=[];books=[];cost=[];mix=[]
    for plane,base in enumerate([pal0,pal1]):
        prior=None if plane==0 else {
            "slots":set(selections[0]),
            "rgb":np.asarray([
                gen["gen_to_rgb"](word) for word in palettes[0][0,7:16]],float)
        }
        p,slots=pick_palette(base,refpal,gen,target,w,groups,plane,prior)
        palettes.append(p);selections.append(slots)
        book,loss,mixed=pick_pairs(p,target,eight,w,groups)
        books.append(book);cost.append(loss);mix.append(mixed)
    # Both planes now have complementary free-slot palettes.
    # Preserve the two-planar advantage without introducing false flat hues.
    assert not set(selections[0]).intersection(selections[1]), (
        "two planes redundantly allocated the same 8x8 source colors",selections)
    # Matching the same source on both planes: enforce strict similarity for
    # neutrals; use looser penalty for genuinely chromatic material.
    seam=((mix[0][:,None,:]-mix[1][None,:,:])**2).sum(-1)
    penalties=np.where(groups==0,.5,.045)[:,None,None]*seam[None,:,:]
    candidate=cost[0][:,:,None]+cost[1][:,None,:]+penalties
    selected=np.argmin(candidate.reshape(256,225),axis=1)
    walls=[(selected//15)+1,(selected%15)+1]
    # Keep baseline flats bit-exact in CRAM and in codebook indices.
    assert np.array_equal(palettes[0][:,:7],palettes[1][:,:7])
    assert np.array_equal(palettes[0][:,:7],pal0[:,:7])
    for book in books:
        assert np.array_equal(book[1:7],np.array([[i,i] for i in range(1,7)]))
    source=[
        "/* R57 experimental 8x8-guided hue-balanced Pair-V. OFFLINE LUTs. */",
        "#ifndef R56_TABLES_H","#define R56_TABLES_H","#include <stdint.h>",
        "#define R56_ANCHORS 6"]
    for name,arr,dtype in [
        ("r56_pal0",palettes[0],"uint16_t"),("r56_pal1",palettes[1],"uint16_t"),
        ("r56_pairs_even",books[0],"uint8_t"),("r56_pairs_odd",books[1],"uint8_t"),
        ("r56_wall_even",walls[0],"uint8_t"),("r56_wall_odd",walls[1],"uint8_t"),
        ("r56_flat_even",flat[0],"uint8_t"),("r56_flat_odd",flat[1],"uint8_t"),
        ("r56_comp_even",walls[0][cm],"uint8_t"),
        ("r56_comp_odd",walls[1][cm],"uint8_t")]:
        source.append(emit(name,arr,dtype))
    source.append("#endif")
    Path(args.out).write_text("\n".join(source)+"\n")
    colors=[[gen["gen_to_rgb"](int(w)) for w in p[0,7:16]] for p in palettes]
    actual=[mix[p][walls[p]-1] for p in range(2)]
    de=[np.sqrt(((actual[i]-tl)**2).sum(-1)) for i in range(2)]
    report={"variant":"R57 ColorMatch K6 8x8-guided",
            "model":"CIELAB dE76, RGB linear-light 50/50, not measured CRT",
            "preserved_flat_anchors":6,"palette_slots_from_8x8":selections,
            "palette_rgb_free_slots":colors,
            "unique_cram_words_union_normal":len(set(palettes[0][0]).union(palettes[1][0])),
            "shared_free_color_source_slots":len(set(selections[0]).intersection(selections[1])),
            "codes_per_plane":15,"extra_codes_per_plane":9,
            "mixed_code_count_per_plane":[int(np.count_nonzero(book[1:,0]!=book[1:,1])) for book in books],
            "hue_family_weights":{name:round(float(w[groups==i].sum()),5)
                                  for i,name in enumerate(("neutral",)+FAMILIES)},
            "weighted_Lab_error_per_plane":[float(np.dot(w,x)) for x in de],
            "weighted_A_B_same_target_dE":float(np.dot(w,np.sqrt(seam[
                walls[0]-1,walls[1]-1]))),
            "warning":"Uncalibrated proxy; gameplay screenshots and FPS needed."}
    Path(args.report).write_text(json.dumps(report,indent=2)+"\n")
    print("R57 ColorMatch report:",json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
