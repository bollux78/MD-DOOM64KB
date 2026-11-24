#!/usr/bin/env python3
"""Shareware weapon frames, signed 6.65 kHz XGM2 samples, level specials."""
from pathlib import Path
import sys,struct,math,os
import numpy as np
from conv import Wad,read_patch
from md_dither import DAC, dither
w=Wad(sys.argv[1]);out=Path(sys.argv[2]);pal=np.frombuffer(w.get('PLAYPAL')[:768],np.uint8).reshape(256,3).astype(float)
sets=[('PUNG','ABCD',None),('PISG','ABCB','PISF'),('SHTG','AABC','SHTF'),('CHGG','ABAB','CHGF'),('MISG','ABAB','MISF'),('SAWG','CDAB',None)]
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
 scale=min(1.,128/(x1-x0),80/(y1-y0))
 y1=min(168,y1)   # the 168-line Doom view ends here; the status bar covers the rest of the sprite
 ww=max(1,round((x1-x0)*scale));hh=max(1,round((y1-y0)*scale))
 for c in canv:
  a=np.full((80,128),-1,np.int16)
  for y in range(hh):
   for x in range(ww):a[80-hh+y,(128-ww)//2+x]=c[y0+min(y1-y0-1,int(y/scale)),x0+min(x1-x0-1,int(x/scale))]
  frames.append(a)
if os.environ.get("DREAD_WEAPON_DUMP"):
 from PIL import Image
 d=Path(os.environ["DREAD_WEAPON_DUMP"]);d.mkdir(parents=True,exist_ok=True)
 nm=['soco','pistola','escopeta','metralhadora','lanca-foguetes','motosserra'];ph=[['pronta','fogo1','fogo2','fogo3'],['pronta','fogo1','fogo2','fogo3'],['pronta','fogo1','fogo2','fogo3'],['pronta','fogo1','fogo2','fogo3'],['pronta','fogo1','fogo2','fogo3'],['idle-C','idle-D','ataque-A','ataque-B']]
 sheet=Image.new('RGBA',(128*4,80*6),(0,0,0,0))
 for i,fr in enumerate(frames):
  a=np.zeros((80,128,4),np.uint8);m=fr>=0;a[m,:3]=pal[fr[m]].astype(np.uint8);a[m,3]=255
  im=Image.fromarray(a);im.save(d/('%d_%s_%d_%s.png'%(i//4,nm[i//4],i%4,ph[i//4][i%4])));sheet.paste(im,((i%4)*128,(i//4)*80))
 sheet.save(d/'folha_completa_128x80.png')
# One 15-colour palette PER weapon (swapped when the weapon changes). k-means over the pixels, seeded by luminance
# quantiles and weighted by use, so the greys of the metal are kept instead of being pulled toward the skin/brown tones.
def fit(fr):
 used=np.concatenate([a[a>=0] for a in fr]);X=pal[used]
 lum=X@np.array([.299,.587,.114]);C=X[np.argsort(lum,kind='stable')[np.linspace(0,len(X)-1,15,dtype=int)]].copy()
 for _ in range(60):
  ids=((X[:,None]-C[None])**2).sum(2).argmin(1)
  for i in range(15):
   if np.any(ids==i):C[i]=X[ids==i].mean(0)
 lv=np.abs(C[:,:,None]-DAC[None,None,:]).argmin(2);return lv
weapon_dither=os.environ.get("DREAD_WEAPON_DITHER","0")=="1"
BAYER=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]])/16.0-0.5
def bayer(rgb,colors,mask):
 # ordered dither: the SAME offset on R,G and B (grey noise), so no coloured dots; step ~ the DAC level spacing (36)
 h,w=rgb.shape[:2];out=np.zeros((h,w),np.uint8);amp=float(os.environ.get("DREAD_BAYER_AMP","30"))
 for y in range(h):
  for x in range(w):
   if mask[y,x]:
    v=np.clip(rgb[y,x]+BAYER[y&3,x&3]*amp,0,255);out[y,x]=((colors-v)**2).sum(1).argmin()
 return out
indexed=[];pals=[]
pdir=Path(__file__).resolve().parent/'weapon_src'/'palettized'
nmw=['soco','pistola','escopeta','metralhadora','lanca-foguetes','motosserra']
if os.environ.get("DREAD_FREEDOOM")=="1":
 from PIL import Image
 from studio_quantizer import Settings,quantize
 for wi in range(6):
  sheet=np.zeros((80,512,4),np.uint8)
  for f,frame in enumerate(frames[wi*4:wi*4+4]):
   m=frame>=0
   tile=sheet[:,f*128:(f+1)*128]
   tile[m,:3]=pal[frame[m]].astype(np.uint8);tile[m,3]=255
  result=quantize(Image.fromarray(sheet),Settings(palettes=1,colors=16,iterations=40,dither="diagonal2",dither_strength=1.0,transparent=True))
  for f in range(4): indexed.append(result.indices[:,f*128:(f+1)*128].copy())
  pals.append([(int(b)//34<<9)|(int(g)//34<<5)|(int(r)//34<<1) for r,g,b in result.palettes_rgb[0]])
  result.preview.save(Path(os.environ["DREAD_FREEDOOM_PREVIEWS"])/("weapon-%d.png"%wi))
elif all((pdir/('%d_%s_pal.png'%(i,nmw[i]))).exists() for i in range(6)) and os.environ.get("DREAD_WEAPON_PALETTIZED","1")=="1":
 # Hand-converted weapon sheets (user): 512x80 = 4 frames of 128x80, <=15 opaque colours + transparent, one palette per weapon.
 from PIL import Image
 for wi in range(6):
  im=np.asarray(Image.open(pdir/('%d_%s_pal.png'%(wi,nmw[wi]))).convert('RGBA'));assert im.shape==(80,512,4)
  op=im[im[:,:,3]>=128][:,:3];cols=np.unique(op,axis=0);assert len(cols)<=15,(wi,len(cols))
  cols=cols[np.argsort(cols@np.array([.299,.587,.114]),kind='stable')]
  lv=np.clip(np.rint(cols/34.0),0,7).astype(int)        # the sheets use the 0,34,..,238 steps = Mega Drive levels 0..7
  lut={tuple(c):i+1 for i,c in enumerate(cols.tolist())}
  for f in range(4):
   fr=im[:,f*128:(f+1)*128];idx=np.zeros((80,128),np.uint8)
   for y in range(80):
    for x in range(128):
     if fr[y,x,3]>=128:idx[y,x]=lut[tuple(int(v) for v in fr[y,x,:3])]
   indexed.append(idx)
  pals.append([0]+[(int(b)*2<<8)|(int(g)*2<<4)|(int(r)*2) for r,g,b in lv]+[0]*(15-len(lv)))
else:
 for wi in range(6):
  fr=frames[wi*4:wi*4+4];levels=fit(fr);rgb=DAC[levels].astype(float)
  lut=np.r_[1+((pal[:,None]-rgb[None])**2).sum(2).argmin(1),0]
  for frame in fr:
   mask=frame>=0
   if weapon_dither:
    idx=bayer(pal[np.maximum(frame,0)],rgb,mask).astype(np.uint8)+1;idx[~mask]=0
   else:idx=lut[frame]
   indexed.append(idx)
  pals.append([0]+[(int(b)*2<<8)|(int(g)*2<<4)|(int(r)*2) for r,g,b in levels])
if os.environ.get("DREAD_WEAPON_PREVIEW"):
 from PIL import Image
 pv=Image.new('RGB',(128*4*2,80*6*2))
 for i,a in enumerate(indexed):
  tab=np.array([[0,0,0]]+[[((c&14)>>1)*36.43,(((c>>4)&14)>>1)*36.43,(((c>>8)&14)>>1)*36.43] for c in pals[i//4][1:]],np.uint8)
  pv.paste(Image.fromarray(tab[a]).resize((256,160),Image.NEAREST),((i%4)*256,(i//4)*160))
 pv.save(os.environ["DREAD_WEAPON_PREVIEW"])
pieces=[(x,y,4,min(32,80-y)//8) for y in range(0,80,32) for x in range(0,128,32)]
unique=[];lookup={};refs=[]
for a in indexed:
 for px,py,cw,ch in pieces:
  for cx in range(cw):
   for cy in range(ch):
    words=[]
    for y in range(8):
     v=0
     for x in range(8):v=(v<<4)|int(a[py+cy*8+y,px+cx*8+x])
     words.append(v)
    key=tuple(words)
    if key not in lookup:lookup[key]=len(unique);unique.append(key)
    refs.append(lookup[key])
s=['#include "mapdata.h"','const uint16_t weap_pals[6][16]={'+','.join('{'+','.join(map(str,q))+'}' for q in pals)+'};','const uint16_t weap_pal[16]={'+','.join(map(str,pals[1]))+'};','const uint16_t weap_x=96,weap_y=64,weap_tiles=160,weap_nframes=24,weap_npieces=12;','const uint8_t weap_piece[12][4]={'+','.join('{'+','.join(map(str,p))+'}' for p in pieces)+'};','const uint16_t weap_frame_refs['+str(len(refs))+']={'+','.join(map(str,refs))+'};','const uint32_t weap_data['+str(len(unique)*8)+']={'+','.join(hex(v) for t in unique for v in t)+'};']
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
mask_id={name:'mask_'+str(i) for i,name in enumerate(sorted(maskdata))}
for name,data in maskdata.items():s.append('static const uint8_t '+mask_id[name]+'['+str(len(data))+']={'+','.join(map(str,data))+'};')
for m in range(1,2 if os.environ.get("DREAD_FREEDOOM")=="1" else 10):
 i=w.find('E1M'+str(m));sides=w.idx(i+3);names=set()
 for j in range(0,len(sides),30):
  for k in [4,12,20]:
   name=sides[j+k:j+k+8].rstrip(b'\0').decode()
   if name in defs:names.add(name)
 names=sorted(names)
 s.append('static const uint8_t *const masks%d[%d]={%s};'%(m,len(names),','.join(mask_id[n] if n in maskdata else '0' for n in names)))
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
print('WAD-original weapon tiles:',len(unique),'frames:',len(frames),'dither:',int(weapon_dither),'PCM bytes:',sum(lens))
