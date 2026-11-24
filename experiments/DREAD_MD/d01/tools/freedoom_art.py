"""Freedoom-only art; exact Tile Palette Studio quantizer."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from conv import Wad,read_patch
from studio_quantizer import Settings,quantize
w=Wad(sys.argv[1]);out=Path(sys.argv[2]);pv=Path(sys.argv[3]);pv.mkdir(parents=True,exist_ok=True)
pal=np.frombuffer(w.get("PLAYPAL")[:768],np.uint8).reshape(256,3)
def art(name,size):
 a=read_patch(w.get(name))
 return Image.fromarray(pal[np.maximum(a,0)]).resize(size,Image.Resampling.NEAREST)
def quant(im,n,name):
 r=quantize(im,Settings(palettes=n,colors=16,iterations=40,dither="diagonal2",dither_strength=1.0))
 r.preview.save(pv/(name+".png"));return r
def words(r):
 return [int("".join(format(int(i),"x") for i in row),16) for tile in r.indices.reshape(28,8,40,8).transpose(0,2,1,3).reshape(-1,8,8) for row in tile]
def cram(r):
 return [(int(b)//34<<9)|(int(g)//34<<5)|(int(a)//34<<1) for a,g,b in r.palettes_rgb.reshape(-1,3)]
def arr(t,n,v):
 return "const "+t+" "+n+"["+str(len(v))+"]={"+",".join(map(str,v))+"};\n"
# Static screens are made by hand (Freedoom TITLEPIC / INTERPIC converted by the author with Tile Palette Studio,
# 320x224, MD colour levels).  Here the PNG is only packed into tiles: index 0 is one shared colour, every
# 8x8 tile gets one of up to N palettes of 15 colours.
import random
SRC=Path(__file__).resolve().parent/"freedoom_screens"
def solve_palettes(sets,npal,cache):
  """Pack every tile's colour set into one of npal sets of <=15 colours (exact MILP via scipy/HiGHS).
  The solution is cached next to the PNG so a build machine without scipy can still run."""
  import json
  allc=sorted(set().union(*sets))
  if npal==1:
    assert len(allc)<=15;groups=[set(allc)]
  elif cache.exists():
    groups=[set(g) for g in json.loads(cache.read_text())]
  else:
    from scipy.optimize import milp,LinearConstraint,Bounds
    from scipy.sparse import lil_matrix
    uniq=sorted(set(sets),key=lambda u:-len(u));ci={c:i for i,c in enumerate(allc)}
    K=npal;C=len(allc);T=len(uniq);nx=C*K;n=nx+T*K
    X=lambda c,p:c*K+p;Y=lambda t,p:nx+t*K+p
    A=lil_matrix((T+sum(len(u)*K for u in uniq)+K,n));lo=[];hi=[];r=0
    for t in range(T):
      for p in range(K):A[r,Y(t,p)]=1
      lo.append(1);hi.append(1);r+=1
    for t,u in enumerate(uniq):
      for p in range(K):
        for c in u:A[r,Y(t,p)]=1;A[r,X(ci[c],p)]=-1;lo.append(-np.inf);hi.append(0);r+=1
    for p in range(K):
      for c in range(C):A[r,X(c,p)]=1
      lo.append(0);hi.append(15);r+=1
    res=milp(c=np.zeros(n),constraints=LinearConstraint(A[:r].tocsr(),lo,hi),integrality=np.ones(n),bounds=Bounds(0,1),options={"time_limit":120.0})
    assert res.x is not None,"palette packing infeasible with %d palettes"%npal
    x=np.round(res.x).astype(int)
    groups=[{allc[c] for c in range(C) if x[X(c,p)]} for p in range(K)]
    cache.write_text(json.dumps([sorted(g) for g in groups]))
  assign=[]
  for s_ in sets:
    k=next((k for k,g in enumerate(groups) if s_<=g),None);assert k is not None,"tile not covered";assign.append(k)
  return groups,assign
def pack(png,npal):
 a=np.asarray(Image.open(SRC/png).convert("RGB")).astype(int);assert a.shape==(224,320,3)
 lv=a//34;assert (a==lv*34).all() and lv.max()<=7
 code=(lv[...,0]<<6)|(lv[...,1]<<3)|lv[...,2]
 tiles=code.reshape(28,8,40,8).transpose(0,2,1,3).reshape(1120,64)
 sets=[frozenset(t.tolist()) for t in tiles]
 # Mega Drive: palette index 0 is transparent on a plane, so it stays unused (black backdrop); colours use 1..15.
 best=solve_palettes(sets,npal,SRC/(png[:-4]+'.palettes.json'))
 assert best,png+": cannot fit tiles into %d palettes of 15 colours"%npal
 groups,assign=best
 white=(7<<6)|(7<<3)|7
 order=sorted(range(len(groups)),key=lambda k:(white in groups[k] and npal>1,k))   # palette holding white goes last (PAL3)
 remap={old:new for new,old in enumerate(order)};groups=[groups[k] for k in order];assign=[remap[k] for k in assign]
 def lay(g,last):
  if last and npal>1 and white in g:   # SGDK menu text uses PAL3 ink 15, keep white there
   o=sorted(g-{white});return [0]+o+[0]*(14-len(o))+[white]
  o=sorted(g);return [0]+o+[0]*(15-len(o))
 pals=[lay(g,k==len(groups)-1) for k,g in enumerate(groups)]
 def cr(c):return 0 if c==0 else ((c&7)<<9)|(((c>>3)&7)<<5)|(((c>>6)&7)<<1)   # code = r<<6|g<<3|b  -> CRAM bbb0ggg0rrr0
 cram=[]
 for p in pals:cram+=[cr(c) for c in p]
 words=[]
 for i,t in enumerate(tiles):
  idx={c:k for k,c in enumerate(pals[assign[i]]) if k and c not in ()}
  for y in range(8):
   w_=0
   for x in range(8):w_=(w_<<4)|idx[int(t[y*8+x])]
   words.append(w_)
 return cram,assign,words
cram,assign,words_=pack("TITLEPIC_pal.png",4)
Image.open(SRC/"TITLEPIC_pal.png").save(pv/"opening.png")
p=list(cram)
assert len(p)==64
(out/"title.c").write_text('#include "mapdata.h"\nconst uint16_t title_ntiles=1120;\n'+arr("uint16_t","title_pal",p)+arr("uint16_t","title_mapa",[0]*1120)+arr("uint16_t","title_mapb",[(a<<13)|i for i,a in enumerate(assign)])+arr("uint32_t","title_tiles",words_))
cram,assign,words_=pack("INTERPIC_pal.png",1)
Image.open(SRC/"INTERPIC_pal.png").save(pv/"intermission.png")
p=cram+[0]*47+[0xeee];assert len(p)==64;tp=assign
packed=[sum(int(tp[i+k])<<(6-2*k) for k in range(4)) for i in range(0,1120,4)]
# Credits/finale are blank placeholders (no episode ending in a single-map build); return to title after the map.
(out/"ending_data.c").write_text('#include <types.h>\n'+arr("u16","inter_pal",p)+arr("u8","inter_tilepal2",packed)+arr("u32","freedoom_inter_tiles",words_)+arr("u8","inter_data",[0])+arr("u8","ending_refs12",[0]*5041)+arr("u8","ending_attrs5",[0]*2101)+arr("u16","ending_pal",[0]*192)+arr("u32","ending_tiles",[0]*8)+arr("u16","finale_pal",[0]*16)+arr("u32","finale_tiles",[0]*512)+'const char *const finale_lines[]={"FREEDOOM PHASE 1"};\nconst u16 finale_nlines=1;\n')
# Compose SKY1 using WAD texture definitions and patches, not Doom's external PNG.
import struct
pn=w.get("PNAMES");names=[pn[4+8*i:12+8*i].rstrip(b"\0").decode() for i in range(struct.unpack_from("<I",pn)[0])]
for tn in ("TEXTURE1","TEXTURE2"):
 t=w.get(tn)
 if not t:continue
 for off in struct.unpack_from("<%dI"%struct.unpack_from("<I",t)[0],t,4):
  if t[off:off+8].rstrip(b"\0")!=b"SKY1":continue
  width,height=struct.unpack_from("<HH",t,off+12);n=struct.unpack_from("<H",t,off+20)[0]
  canvas=np.zeros((height,width),np.int16)
  for i in range(n):
   x,y,j=struct.unpack_from("<hhH",t,off+22+10*i);a=read_patch(w.get(names[j]))
   for yy,xx in zip(*np.where(a>=0)):
    if 0<=y+yy<height and 0<=x+xx<width:canvas[y+yy,x+xx]=a[yy,xx]
  Image.fromarray(pal[canvas]).resize((256,72),Image.Resampling.NEAREST).save(pv/"sky.png")
  break
assert (pv/"sky.png").exists()
