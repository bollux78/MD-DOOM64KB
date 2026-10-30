#!/usr/bin/env python3
"""R93c (Claudio): brown-hue compromise search on SH1 p=0 CRAM. OFFLINE ONLY, no build input written.
Only slots feeding brown targets (C>10, hue 30..95 deg), each channel within +-1 of SH1.
Objective: brown hue error (linear DAC proxy + HW DAC table). Aggregate limits per DAC model:
look distance to SH1 <= 1.5 dE, shadow share +-3 points, mean L +-1, mean dE not worse by >0.2,
brown chroma bias within max(4, SH1). Codes and joint states always follow the production R79/R91 remap.
Per-code guards of r93b are NOT enforced here: violations are reported by r93b-style checks (compromise).
usage: r93c_brown_search.py TABLES KEYS_DIR WERK_JSON OUT_JSON
"""
import numpy as np,json,importlib.util,itertools,sys
from pathlib import Path
TABLES,KEYS,WERK,OUT=sys.argv[1:5]
spec=importlib.util.spec_from_file_location('st',str(Path(__file__).with_name('r93b_cram_study.py')));st=importlib.util.module_from_spec(spec);spec.loader.exec_module(st)
text=Path(TABLES).read_text()
HW=np.array([0,52,87,116,144,172,206,255.])
def rgbhw(w):
  w=np.asarray(w);return np.stack([HW[(w>>1)&7],HW[(w>>5)&7],HW[(w>>9)&7]],-1)
def ev(mode,keys,words,dac,ref=None):
  code,err,_=mode.tables(words)
  f=rgbhw if dac=='HW' else st.rgb
  tg=np.array([st.avg(f(mode.base[b,0]),f(mode.base[b,0])[mode.part[b]]) for b in (0,1)]);tl=st.to_lab(tg)
  sh=np.array([[st.avg(f(words[b]),f(words[b])[mode.part[b]]),st.avg(f(words[b])*.5,f(words[b])[mode.part[b]]*.5)] for b in (0,1)]);sl=st.to_lab(sh)
  idx=np.nonzero(keys)[0];w=keys[idx];ka,kb=idx>>8,idx&255
  c=lambda s,b,x:err[b,s,x>>4]+err[b,s,x&15]
  sh_=(c(1,0,ka)+c(1,1,kb))<(c(0,0,ka)+c(0,1,kb));stt=sh_.astype(int)
  N=np.zeros((2,2,16))
  for b,x in ((0,ka>>4),(0,ka&15),(1,kb>>4),(1,kb&15)):np.add.at(N,(b,stt,x),w)
  N[:,:,0]=0;tot=N.sum()
  shown=sl[np.arange(2)[:,None,None],np.arange(2)[None,:,None],code]
  t=tl[:,None];tC=st.chroma(tl)[:,None];th=st.hue(tl)[:,None]
  brown=(tC>10)&(th>30)&(th<95);bw=(N*brown).sum()
  dh=(st.hue(shown)-th+180)%360-180
  r=dict(shown=shown,N=N,dE=float((N*np.linalg.norm(shown-t,axis=-1)).sum()/tot),
    bh=float((N*brown*np.abs(dh)).sum()/bw),bhs=float((N*brown*dh).sum()/bw),bC=float((N*brown*(st.chroma(shown)-tC)).sum()/bw),
    L=float((N*shown[...,0]).sum()/tot),shadow=float(w[sh_&(idx!=0)].sum()/w[idx!=0].sum()))
  if ref is not None: r['look']=float((N*np.linalg.norm(shown-ref['shown'],axis=-1)).sum()/tot)
  return r
out={}
werk=json.loads(Path(WERK).read_text())['palettes']
for name,prefix,mi in st.MODES:
  mode=st.Mode(text,prefix);keys=np.load(Path(KEYS)/f'keys-{name}.npy').astype(float)
  w0=np.array([st.sh1_words(mode.base[b,0]) for b in (0,1)])
  ref={d:ev(mode,keys,w0,d) for d in ('LIN','HW')}
  # slots feeding brown target codes
  tC=mode.tC;th=mode.tH;brownc=(tC>10)&(th>30)&(th<95)
  slots=sorted({(b,s) for b in (0,1) for c in range(1,16) if brownc[b,c] for s in (c,int(mode.part[b][c]))})
  def score(words):
    r={d:ev(mode,keys,words,d,ref[d]) for d in ('LIN','HW')}
    ok=all(r[d]['look']<=1.5 and abs(r[d]['shadow']-ref[d]['shadow'])<=0.03 and r[d]['dE']<=ref[d]['dE']+0.2 and abs(r[d]['L']-ref[d]['L'])<=1.0 and abs(r[d]['bC'])<=max(4,abs(ref[d]['bC'])) for d in r)
    return r['LIN']['bh']+r['HW']['bh'],ok,r
  words=w0.copy();cur,_,_=score(words)
  for sweep in range(2):
    for b,s in slots:
      c0=np.array([(w0[b,s]>>1)&7,(w0[b,s]>>5)&7,(w0[b,s]>>9)&7])
      best=None
      for d in itertools.product((-1,0,1),repeat=3):
        cc=np.clip(c0+d,0,7);wd=(cc[0]<<1)|(cc[1]<<5)|(cc[2]<<9)
        if wd==words[b,s]:continue
        keep=words[b,s];words[b,s]=wd;sc,ok,r=score(words);words[b,s]=keep
        if ok and sc<cur-0.2 and (best is None or sc<best[0]):best=(sc,wd)
      if best:cur=best[0];words[b,s]=best[1]
  _,ok,r=score(words);wk=np.array([np.array(werk[mi-1][b][0]) for b in (0,1)]);_,okw,rw=score(wk)
  fmt=lambda x:{k:round(v,2) for k,v in x.items() if k not in('shown','N')}
  t=lambda w:tuple(int(v) for v in ((w>>1)&7,(w>>5)&7,(w>>9)&7))
  ch=[(b,s,t(w0[b,s]),t(words[b,s])) for b in (0,1) for s in range(16) if words[b,s]!=w0[b,s]]
  print(name,'brown slots',slots);print(' SH1',{d:fmt(ref[d]) for d in ref});print(' R93c',{d:fmt(r[d]) for d in r});print(' R93(werk)',{d:fmt(rw[d]) for d in rw},'within limits',okw);print(' changes',ch)
  out[name]=dict(changes=ch,sh1={d:fmt(ref[d]) for d in ref},r93c={d:fmt(r[d]) for d in r},werk={d:fmt(rw[d]) for d in rw},werk_within=okw,words=words.tolist())
Path(OUT).write_text(json.dumps(out,indent=1,default=str))
