#!/usr/bin/env python3
"""Shareware weapon frames, signed 6.65 kHz XGM2 samples, level specials."""
from pathlib import Path
import sys,struct,math
import numpy as np
from conv import Wad,read_patch
w=Wad(sys.argv[1]);out=Path(sys.argv[2]);pal=np.frombuffer(w.get('PLAYPAL')[:768],np.uint8).reshape(256,3).astype(float)
sets=[('PUNG','ABCD',None),('PISG','ABCB','PISF'),('SHTG','AABC','SHTF'),('CHGG','ABAB','CHGF'),('MISG','ABAB','MISF'),('SAWG','ABAB',None)]
frames=[]
for prefix,letters,flash in sets:
 canv=[]
 for f,letter in enumerate(letters):
  c=np.full((200,320),-1,np.int16)
  for nm in [prefix+letter+'0']+([flash+'A0'] if flash and f==1 else []):
   d=w.get(nm)
   if not d:continue
   a=read_patch(d);h,ww=a.shape;_,_,lo,to=struct.unpack_from('<HHhh',d)
   xx,yy=1-lo,16-to
   for y in range(h):
    for x in range(ww):
     if a[y,x]>=0 and 0<=y+yy<200 and 0<=x+xx<320:c[y+yy,x+xx]=a[y,x]
  canv.append(c)
 ys,xs=np.nonzero(np.any(np.asarray(canv)>=0,axis=0));x0,x1=xs.min(),xs.max()+1;y0,y1=ys.min(),min(184,ys.max()+1)
 scale=min(1.,128/(x1-x0),80/(y1-y0));ww=max(1,round((x1-x0)*scale));hh=max(1,round((y1-y0)*scale))
 for c in canv:
  a=np.full((80,128),-1,np.int16)
  for y in range(hh):
   for x in range(ww):a[80-hh+y,(128-ww)//2+x]=c[y0+min(y1-y0-1,int(y/scale)),x0+min(x1-x0-1,int(x/scale))]
  frames.append(a)
# deterministic palette over all weapons, preserving transparent index zero.
used=np.unique(np.concatenate([a[a>=0] for a in frames]));X=pal[used];C=X[np.linspace(0,len(X)-1,15,dtype=int)].copy()
for _ in range(40):
 ids=((X[:,None]-C[None])**2).sum(2).argmin(1)
 for i in range(15):
  if np.any(ids==i):C[i]=X[ids==i].mean(0)
levels=np.clip(np.rint(C/36.43),0,7).astype(int);rgb=levels*36.43
lut=np.r_[1+((pal[:,None]-rgb[None])**2).sum(2).argmin(1),0]
pieces=[(x,y,4,min(32,80-y)//8) for y in range(0,80,32) for x in range(0,128,32)]
unique=[];lookup={};refs=[]
for a in frames:
 for px,py,cw,ch in pieces:
  for cx in range(cw):
   for cy in range(ch):
    words=[]
    for y in range(8):
     v=0
     for x in range(8):v=(v<<4)|int(lut[a[py+cy*8+y,px+cx*8+x]])
     words.append(v)
    key=tuple(words)
    if key not in lookup:lookup[key]=len(unique);unique.append(key)
    refs.append(lookup[key])
md=[0]+[(int(b)*2<<8)|(int(g)*2<<4)|(int(r)*2) for r,g,b in levels]
s=['#include "mapdata.h"','const uint16_t weap_pal[16]={'+','.join(map(str,md))+'};','const uint16_t weap_x=96,weap_y=64,weap_tiles=160,weap_nframes=24,weap_npieces=12;','const uint8_t weap_piece[12][4]={'+','.join('{'+','.join(map(str,p))+'}' for p in pieces)+'};','const uint16_t weap_frame_refs['+str(len(refs))+']={'+','.join(map(str,refs))+'};','const uint32_t weap_data['+str(len(unique)*8)+']={'+','.join(hex(v) for t in unique for v in t)+'};']
(out/'weapon.c').write_text('\n'.join(s)+'\n')
# XGM2 data must start on 256-byte boundaries, and length be a multiple of 256.
names=['PISTOL','SHOTGN','PUNCH','SAWFUL','RLAUNC','BAREXP','ITEMUP','WPNUP','DOROPN','DORCLS','SWTCHN','PLPAIN','POSIT1','PODTH1','SGTSIT','SGTDTH','BGACT','BGDTH1','SLOP','TELEPT','PLDETH']
s=['#include <types.h>'];ptr=[];lens=[]
for i,name in enumerate(names):
 d=w.get('DS'+name)
 if not d:d=w.get('DSPISTOL')
 fmt,rate,n=struct.unpack_from('<HHI',d);assert fmt==3 and rate>0
 a=np.frombuffer(d[8:8+n],np.uint8).astype(float)-128
 if len(a)>32:a=a[16:-16]
 nout=max(1,round(len(a)*6650/rate));a=np.interp(np.arange(nout)*rate/6650,np.arange(len(a)),a)
 a=np.rint(np.clip(a,-127,127)).astype(np.int8).tobytes();a+=bytes((-len(a))%256)
 s.append('static const u8 sample_%d[%d] __attribute__((aligned(256)))={%s};'%(i,len(a),','.join(map(str,a))));ptr.append('sample_'+str(i));lens.append(len(a))
s+=['const u8 *const game_sfx[21]={'+','.join(ptr)+'};','const u32 game_sfx_len[21]={'+','.join(map(str,lens))+'};']
(out/'sfx_data.c').write_text('\n'.join(s)+'\n')
# Compose coverage masks independently from colour bytes (0xFF is a valid colour pair).
pn=w.get('PNAMES');pnames=[pn[4+8*i:12+8*i].rstrip(b'\0').decode() for i in range(struct.unpack_from('<I',pn)[0])]
patches=w.range(('P_START','PP_START'),('P_END','PP_END'));defs={}
for tn in ['TEXTURE1','TEXTURE2']:
 d=w.get(tn)
 if not d:continue
 for off in struct.unpack_from('<%dI'%struct.unpack_from('<I',d)[0],d,4):
  name=d[off:off+8].rstrip(b'\0').decode();ww,hh=struct.unpack_from('<HH',d,off+12);n=struct.unpack_from('<H',d,off+20)[0]
  defs[name]=(ww,hh,[struct.unpack_from('<hhH',d,off+22+j*10) for j in range(n)])
maskdata={}
for name,(ww,hh,parts) in defs.items():
 a=np.zeros((hh,ww),bool)
 for ox,oy,pi in parts:
  d=patches.get(pnames[pi])
  if not d:continue
  patch=read_patch(d)
  for y in range(patch.shape[0]):
   for x in range(patch.shape[1]):
    if 0<=oy+y<hh and 0<=ox+x<ww and patch[y,x]>=0:a[oy+y,ox+x]=True
 if a.all():continue
 W=1<<max(0,math.ceil(math.log2(max(1,ww//2))));H=1<<max(0,math.ceil(math.log2(hh)))
 bits=[]
 for x in range(W):
  for y in range(H):bits.append(int(a[y%hh,(2*x)%ww] or a[y%hh,(2*x+1)%ww]))
 maskdata[name]=np.packbits(np.array(bits,np.uint8),bitorder='little').tobytes()
s=['#include "levelmeta.h"'];maps=[]
for name,data in maskdata.items():s.append('static const uint8_t mask_'+name+'['+str(len(data))+']={'+','.join(map(str,data))+'};')
for m in range(1,10):
 i=w.find('E1M'+str(m));sides=w.idx(i+3);names=set()
 for j in range(0,len(sides),30):
  for k in [4,12,20]:
   name=sides[j+k:j+k+8].rstrip(b'\0').decode()
   if name in defs:names.add(name)
 names=sorted(names)
 s.append('static const uint8_t *const masks%d[%d]={%s};'%(m,len(names),','.join('mask_'+n if n in maskdata else '0' for n in names)))
 sectors=w.idx(i+8);things=w.idx(i+1);ss=[struct.unpack_from('<h',sectors,j+22)[0] for j in range(0,len(sectors),26)]
 tele=[]
 for j in range(0,len(things),10):
  x,y,angle,t,f=struct.unpack_from('<5h',things,j)
  if t==14:tele.append((x,y,angle))
 flats=[sectors[j+4:j+12] for j in range(0,len(sectors),26)];fn={v:k for k,v in enumerate(sorted(set(flats)))}
 s.append('static const uint16_t flats%d[%d]={%s};'%(m,len(flats),','.join(str(fn[v]) for v in flats)))
 s.append('static const uint16_t sp%d[%d]={%s};'%(m,len(ss),','.join(map(str,ss))))
 s.append('static const int16_t tele%d[%d][3]={%s};'%(m,max(1,len(tele)),','.join('{%d,%d,%d}'%t for t in tele) or '{0,0,0}'))
 maps.append('{sp%d,flats%d,tele%d,%d,masks%d}'%(m,m,m,len(tele),m))
s.append('const LevelMeta level_meta[9]={'+','.join(maps)+'};');(out/'levelmeta.c').write_text('\n'.join(s)+'\n')
print('weapon tiles:',len(unique),'frames:',len(frames),'PCM bytes:',sum(lens))
