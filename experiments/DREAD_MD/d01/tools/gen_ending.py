#!/usr/bin/env python3
"""Pack the user's three approved screens losslessly; WAD finale flat/text."""
from pathlib import Path
import sys,struct,csv,re,ast
import numpy as np
from PIL import Image
from conv import Wad,read_patch
root=Path(__file__).resolve().parent;src=root/'ending_src';out=Path(sys.argv[2]);w=Wad(sys.argv[1])
unique=[];ids={};refs=[];attrs=[];palettes=[]
for name in ['DoomCREDIT10','disclaimer_and_credits','endMD2']:
 if name=='disclaimer_and_credits':
  art=src/'user_h40';raw=(art/'tiles_4bpp.bin').read_bytes();tm=struct.unpack('>1120H',(art/'tilemap_h40.bin').read_bytes())
  palettes.extend(struct.unpack('>64H',(art/'cram_4palettes.bin').read_bytes()))
  for v in tm:
   tile=raw[(v&2047)*32:((v&2047)+1)*32];assert len(tile)==32
   if tile not in ids:ids[tile]=len(unique);unique.append(tile)
   refs.append(ids[tile]);attrs.append(v&0xf800)
  continue
 palette=list(struct.unpack('>64H',(src/(name+'_pal.palettes.cram.be.bin')).read_bytes()));palettes.extend(palette)
 lookup={(int(r['tile_x']),int(r['tile_y'])):int(r['palette_0_to_3']) for r in csv.DictReader(open(src/(name+'_pal_tile_palettes.csv')))}
 im=Image.open(src/(name+'_pal.png')).convert('RGB');ref=[]
 colors=[((c>>1&7)*34,(c>>5&7)*34,(c>>9&7)*34) for c in palette]
 for y in range(28):
  for x in range(40):
   p=lookup[x,y];tile=bytearray()
   for yy in range(8):
    row=[]
    for xx in range(8):
     rgb=im.getpixel((x*8+xx,y*8+yy));matches=[i for i in range(16) if colors[p*16+i]==rgb]
     if not matches:raise ValueError((name,x,y,p,rgb))
     row.append(matches[0])
    tile.extend((row[i]<<4)|row[i+1] for i in range(0,8,2))
   tile=bytes(tile)
   if tile not in ids:ids[tile]=len(unique);unique.append(tile)
   ref.append(ids[tile])
 refs.extend(ref);attrs.extend(lookup[x,y]<<13 for y in range(28) for x in range(40))
s=['#include <types.h>','const u16 ending_refs[3360]={'+','.join(map(str,refs))+'};','const u16 ending_attrs[3360]={'+','.join(map(str,attrs))+'};','const u16 ending_pal[192]={'+','.join(map(str,palettes))+'};','const u32 ending_tiles['+str(len(unique)*8)+']={'+','.join(hex(v) for t in unique for v in struct.unpack('>8I',t))+'};']
# Original E1 finale text already in this repository's Doom source.
text=(root.parents[3]/'src/d_englsh.h').read_text().split('#define E1TEXT',1)[1].split('#endif',1)[0]
text=''.join(ast.literal_eval(x) for x in re.findall(r'"(?:[^"\\]|\\.)*"',text))
lines=text.split('\n');s.append('const char *const finale_lines['+str(len(lines))+']={'+','.join('"'+l.replace('\\','\\\\').replace('"','\\"')+'"' for l in lines)+'};');s.append('const u16 finale_nlines='+str(len(lines))+';')
# Palette 0 for FLOOR4_8, white UI on palette 3.
pal=np.frombuffer(w.get('PLAYPAL')[:768],np.uint8).reshape(256,3);im=Image.fromarray(pal[np.frombuffer(w.get('FLOOR4_8'),np.uint8).reshape(64,64)],'RGB');q=im.quantize(colors=15,dither=Image.Dither.NONE);pp=q.getpalette()[:45];lv=lambda a:max(0,min(7,round(a/36.43)));cram=[0]+[(lv(pp[i+2])<<9)|(lv(pp[i+1])<<5)|(lv(pp[i])<<1) for i in range(0,45,3)]
from md_dither import dither,DAC
colors=np.array([[(c>>1)&7,(c>>5)&7,(c>>9)&7] for c in cram[1:]])
a=dither(np.asarray(im),DAC[colors])+1;words=[]
for ty in range(8):
 for tx in range(8):
  for y in range(8):
   v=0
   for x in range(8):v=(v<<4)|int(a[ty*8+y,tx*8+x])
   words.append(v)
s+=['const u16 finale_pal[16]={'+','.join(map(str,cram))+'};','const u32 finale_tiles[512]={'+','.join(hex(v) for v in words)+'};']
# Native H40 intermission: same original Doom WIMAP0 artwork as supplied reference,
# 320x224 pixels, three independent 15-colour MD palettes, PAL3 reserved for text.
# Quantize the top, middle and bottom thirds separately, then choose the palette
# with minimum tile error, preserving individual 8x8 tiles (no 2x2 pixel scaling).
a=read_patch(w.get('WIMAP0'));a=np.where(a<0,0,a).astype(np.uint8)
im=Image.fromarray(pal[a],'RGB').resize((320,224),Image.Resampling.BILINEAR)
rgb=np.asarray(im,dtype=np.int16)
palettes_rgb=[]
for k in range(3):
 region=Image.fromarray(np.asarray(im)[k*74:min(224,(k+1)*74+2)].copy(),'RGB')
 quant=region.quantize(colors=15,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
 pp=quant.getpalette()
 colors=[]
 for i in range(15):
  rr,gg,bb=pp[3*i:3*i+3]
  colors.append([int(round(rr/36.43))*34,int(round(gg/36.43))*34,int(round(bb/36.43))*34])
 palettes_rgb.append(np.asarray(colors,dtype=np.int16))
inter_pal=[]
for colors in palettes_rgb:
 inter_pal.append(0)
 for rr,gg,bb in colors:
  inter_pal.append((int(bb)//34<<9)|(int(gg)//34<<5)|(int(rr)//34<<1))
inter_pal.extend([0]*16) # PAL3 text uses CRAM entry 63, set by HUD.
tilepal=[];packed=bytearray()
bayer=np.array([[-6,3],[6,-3]],dtype=np.int16)
for ty in range(28):
 for tx in range(40):
  tile=rgb[ty*8:(ty+1)*8,tx*8:(tx+1)*8].copy()
  # Select one of the three hardware palettes for this tile.
  choices=[]
  for colors in palettes_rgb:
   dist=np.sum((tile[:,:,None,:]-colors[None,None,:,:])**2,axis=3)
   choices.append(int(np.min(dist,axis=2).sum()))
  chosen=int(np.argmin(choices));tilepal.append(chosen)
  colors=palettes_rgb[chosen]
  # Subtle ordered 2x2 dither; preserve native H40 spatial detail.
  tile=np.clip(tile+bayer[:,:,None].repeat(4,axis=0).repeat(4,axis=1),0,255)
  dist=np.sum((tile[:,:,None,:]-colors[None,None,:,:])**2,axis=3)
  indices=np.argmin(dist,axis=2).astype(np.uint8)+1
  for yy in range(8):
   for xx in range(0,8,2):
    packed.append(int((indices[yy,xx]<<4)|indices[yy,xx+1]))
assert len(packed)==35840 and len(tilepal)==1120
s+=['const u16 inter_pal[64]={'+','.join(map(str,inter_pal))+'};',
    'const u8 inter_tilepal[1120]={'+','.join(map(str,tilepal))+'};',
    'const u8 inter_data[35840]={'+','.join(map(str,packed))+'};']
print('Intermission: native H40 320x224, 3 palette background, 35840 bytes')
(out/'ending_data.c').write_text('\n'.join(s)+'\n');print('Ending art:',len(unique),'unique tiles,',len(lines),'text lines')
