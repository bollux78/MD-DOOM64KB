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
# Store the intermission background at 160x112 4bpp; expand 2x2 while loading.
# UI remains native resolution. No extra framebuffer or decompression RAM.
a=read_patch(w.get('WIMAP0'));a=np.where(a<0,0,a).astype(np.uint8)
im=Image.fromarray(pal[a],'RGB').resize((160,112),Image.Resampling.NEAREST)
q=im.quantize(colors=15,dither=Image.Dither.NONE);pp=q.getpalette()[:45]
cram=[0]+[(lv(pp[i+2])<<9)|(lv(pp[i+1])<<5)|(lv(pp[i])<<1) for i in range(0,45,3)]
a=np.asarray(q)+1;packed=((a[:,::2]<<4)|a[:,1::2]).flatten()
s+=['const u16 inter_pal[16]={'+','.join(map(str,cram))+'};','const u8 inter_data[8960]={'+','.join(map(str,packed))+'};']
print('Intermission: 8960 bytes packed background, UI native resolution')
(out/'ending_data.c').write_text('\n'.join(s)+'\n');print('Ending art:',len(unique),'unique tiles,',len(lines),'text lines')
