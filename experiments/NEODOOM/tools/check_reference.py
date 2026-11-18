#!/usr/bin/env python3
"""Compare portal surface coverage with independent intersections of Doom SEGS."""
import ctypes as C,json,sys,math
from pathlib import Path
import numpy as np
from doom_wad import directory,load_map
from PIL import Image
root=Path(sys.argv[1]);lib=C.CDLL(str(Path(sys.argv[2]).resolve()));wad=Path(sys.argv[3]);out=Path(sys.argv[4]);out.mkdir(exist_ok=True)
W,H,F=72,40,36
class Camera(C.Structure):_fields_=[('x',C.c_int16),('y',C.c_int16),('z',C.c_int16),('angle',C.c_uint16),('room',C.c_uint16)]
lib.nd_locate.argtypes=[C.c_int16,C.c_int16,C.c_int16];lib.nd_locate.restype=C.c_int16
lib.nd_render.argtypes=[C.POINTER(Camera),C.POINTER(C.c_uint8)]
C.c_uint16.in_dll(lib,'nd_flat').value=1
m=json.loads((root/'src/map.json').read_text());data=load_map(directory(wad.read_bytes()),'E1M1')
vertices,sectors,segs,*_=data
starts=np.array([vertices[a] for a,b,f,k in segs],dtype=float);ends=np.array([vertices[b] for a,b,f,k in segs],dtype=float);edge=ends-starts
colors=np.array([[0,0,0]]*16,dtype=np.uint8);colors[8]=[70,70,70];colors[9]=[110,110,110];colors[12]=[210,210,210]
results=[];total=bad=holes=allbad=0
for pi,(xx,yy,degrees) in enumerate(m['poses']):
 for turn in range(4):
  x,y=xx*4,yy*4;angle=(round(degrees*256/360)+turn*64)&255;r=lib.nd_locate(x,y,-1)
  if r<0:raise AssertionError(('invalid pose',pi))
  eye=m['room_records'][r][2]+41;cam=Camera(x,y,eye,angle,r);buf=(C.c_uint8*(W*H))();lib.nd_render(C.byref(cam),buf)
  actual=np.ctypeslib.as_array(buf).reshape(W,H).T.copy();reference=np.zeros((H,W),dtype=np.uint8)
  cs=round(256*math.sin(((angle+64)&255)*math.tau/256));sn=round(256*math.sin(angle*math.tau/256));origin=np.array([xx,yy],float)
  delta=starts-origin;front=edge[:,0]*(yy-starts[:,1])-edge[:,1]*(xx-starts[:,0])<0
  for col in range(W):
   slope=math.trunc((2*col+1-W)*128/F);dx=cs+((sn*slope)>>8);dy=sn-((cs*slope)>>8);ray=np.array([dx,dy],float)/256
   den=ray[0]*edge[:,1]-ray[1]*edge[:,0]
   with np.errstate(divide='ignore',invalid='ignore'):
    t=(delta[:,0]*edge[:,1]-delta[:,1]*edge[:,0])/den;u=(delta[:,0]*ray[1]-delta[:,1]*ray[0])/den
   hit=np.where(front&(t>0.25)&(u>=0)&(u<=1))[0];hit=sorted(hit,key=lambda i:t[i])
   for row in range(H):
    for i in hit:
     a,b,fs,bs=segs[i];floor,ceil=sectors[fs];z=eye+(H/2-row)*t[i]/F
     if z>ceil:c=8
     elif z<floor:c=9
     elif bs==65535 or sectors[bs][1]<=floor or sectors[bs][0]>=ceil or sectors[bs][1]<=sectors[bs][0]:c=12
     elif z>sectors[bs][1] or z<sectors[bs][0]:c=12
     else:continue
     reference[row,col]=c;break
  # Exempt one-pixel horizontal/vertical surface boundaries for fixed-point rounding.
  stable=np.ones((H,W),dtype=bool)
  for shift in (-1,1):
   stable&=reference==np.roll(reference,shift,axis=0);stable&=reference==np.roll(reference,shift,axis=1)
  diff=(reference!=actual)&stable;n=int(diff.sum());blank=int(((actual==0)&(reference!=0)&stable).sum())
  total+=int(stable.sum());bad+=n;holes+=blank;allbad+=int((reference!=actual).sum());results.append(dict(pose=pi,turn=turn,stable_pixels=int(stable.sum()),different=n,holes=blank))
  if turn==0 or n>30:
   Image.fromarray(colors[actual]).resize((288,160),Image.Resampling.NEAREST).save(out/f'portal-{pi}-{turn}.png')
   Image.fromarray(colors[reference]).resize((288,160),Image.Resampling.NEAREST).save(out/f'reference-{pi}-{turn}.png')
result=dict(frames=len(results),pixels_including_boundaries=len(results)*W*H,different_including_boundaries=allbad,stable_pixels=total,different=bad,holes=holes,mismatch_fraction=bad/total,results=results)
(out/'reference-check.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='results'})

assert holes==0 and bad/total<0.002, "portal coverage exceeds the prototype tolerance"
