"""Convert supplied weapon sheet, native pixel size, 15-colour MD palette + transparency."""
from pathlib import Path
import sys,struct,numpy as np
from PIL import Image
from md_dither import DAC,dither
root=Path(__file__).resolve().parent;out=Path(sys.argv[1]);sheet=np.asarray(Image.open(root/'weapon_src/guns_optimized_pal.png').convert('RGBA'))
# Explicit crop metadata from transparent gutters. Frames share a bottom anchor.
crops=[[(0,54),(54,94),(94,146),(146,214)],[(291,323),(291,323),(324,364),(365,399)],[(545,573),(545,573),(575,615),(615,646)],[(868,938),(939,1010),(1011,1087),(1088,1164)],[(1252,1300),(1310,1357),(1367,1406),(1409,1448)],[(1516,1584),(1584,1685),(1691,1733),(1739,1784)]]
frames=[]
for weapon,group in enumerate(crops):
 for f,(a,b) in enumerate(group):
  art=sheet[:,a:b].copy();mask=art[:,:,3]>=128;ys,xs=np.nonzero(mask);art=art[ys.min():ys.max()+1,xs.min():xs.max()+1];h,w=art.shape[:2]
  assert w<=128 and h<=76,(weapon,f,w,h)
  canvas=np.zeros((80,128,4),np.uint8);x=(128-w)//2;y=80-h;canvas[y:y+h,x:x+w]=art
  if f==1 and weapon in (1,2):
   a,b=(474,497) if weapon==1 else (705,725);flash=sheet[:,a:b];m=flash[:,:,3]>=128;yy,xx=np.nonzero(m);flash=flash[yy.min():yy.max()+1,xx.min():xx.max()+1];fh,fw=flash.shape[:2]
   # The flare touches the muzzle of the firing pose, not the raised reload pose.
   cx=x+int(np.nonzero(art[:min(5,h),:,3]>=128)[1].mean());fx=cx-fw//2;fy=y-fh+4
   assert fy>=0
   for row in range(fh):
    for col in range(fw):
     if flash[row,col,3]>=128:canvas[fy+row,fx+col]=flash[row,col]
  frames.append(canvas)
# Weighted palette fit on supplied pixels; no rescaling or aspect changes.
X=np.concatenate([a[a[:,:,3]>=128,:3] for a in frames]).astype(float);C=X[np.linspace(0,len(X)-1,15,dtype=int)].copy()
for _ in range(40):
 ids=((X[:,None]-C[None])**2).sum(2).argmin(1)
 for i in range(15):
  if np.any(ids==i):C[i]=X[ids==i].mean(0)
levels=np.abs(C[:,:,None]-DAC[None,None,:]).argmin(2);rgb=DAC[levels]
indexed=[]
for a in frames:
 mask=a[:,:,3]>=128;im=dither(a[:,:,:3],rgb,mask)+1;im[~mask]=0;indexed.append(im)
pieces=[(x,y,4,min(32,80-y)//8) for y in range(0,80,32) for x in range(0,128,32)]
unique=[];lookup={};refs=[]
for a in indexed:
 for px,py,cw,ch in pieces:
  for cx in range(cw):
   for cy in range(ch):
    words=tuple(sum(int(a[py+cy*8+y,px+cx*8+x])<<((7-x)*4) for x in range(8)) for y in range(8))
    if words not in lookup:lookup[words]=len(unique);unique.append(words)
    refs.append(lookup[words])
md=[0]+[(int(b)*2<<8)|(int(g)*2<<4)|(int(r)*2) for r,g,b in levels]
s=['#include "mapdata.h"','const uint16_t weap_pal[16]={'+','.join(map(str,md))+'};','const uint16_t weap_x=96,weap_y=68,weap_tiles=160,weap_nframes=24,weap_npieces=12;','const uint8_t weap_piece[12][4]={'+','.join('{'+','.join(map(str,p))+'}' for p in pieces)+'};','const uint16_t weap_frame_refs[3840]={'+','.join(map(str,refs))+'};','const uint32_t weap_data['+str(len(unique)*8)+']={'+','.join(hex(v) for t in unique for v in t)+'};']
(out/'weapon.c').write_text('\n'.join(s)+'\n');print('User weapons:',len(unique)*32,'bytes unique tiles, native scale')
preview=Image.new('RGBA',(128*4,80*6))
for i,a in enumerate(indexed):
 rgba=np.zeros((80,128,4),np.uint8);rgba[:,:,:3]=np.array([[0,0,0]]+rgb.tolist(),np.uint8)[a];rgba[:,:,3]=np.where(a>0,255,0);preview.paste(Image.fromarray(rgba),((i%4)*128,(i//4)*80))
preview.save(out/'weapon_preview.png')
