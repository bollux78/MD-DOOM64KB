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
# Use 3 palettes for art so PAL3 remains dedicated to UI; preserve all studio output indices.
r=quant(art("TITLEPIC",(320,224)),3,"opening")
p=cram(r)+[0]*15+[0xeee]
(out/"title.c").write_text('#include "mapdata.h"\nconst uint16_t title_ntiles=1120;\n'+arr("uint16_t","title_pal",p)+arr("uint16_t","title_mapa",[0]*1120)+arr("uint16_t","title_mapb",[(int(a)<<13)|i for i,a in enumerate(r.tile_palettes.ravel())])+arr("uint32_t","title_tiles",words(r)))
r=quant(art("WIMAP0",(320,224)),3,"intermission")
p=cram(r)+[0]*15+[0xeee];tp=r.tile_palettes.ravel()
packed=[sum(int(tp[i+k])<<(6-2*k) for k in range(4)) for i in range(0,1120,4)]
# Credits/finale placeholders are blank, not Doom graphics; return to title after map.
(out/"ending_data.c").write_text('#include <types.h>\n'+arr("u16","inter_pal",p)+arr("u8","inter_tilepal2",packed)+arr("u32","freedoom_inter_tiles",words(r))+arr("u8","inter_data",[0])+arr("u8","ending_refs12",[0]*5041)+arr("u8","ending_attrs5",[0]*2101)+arr("u16","ending_pal",[0]*192)+arr("u32","ending_tiles",[0]*8)+arr("u16","finale_pal",[0]*16)+arr("u32","finale_tiles",[0]*512)+'const char *const finale_lines[]={"FREEDOOM PHASE 1"};\nconst u16 finale_nlines=1;\n')
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
