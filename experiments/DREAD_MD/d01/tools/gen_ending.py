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
# Losslessly compress credits map metadata while retaining the original art.
# Nearly all tile references are new sequential IDs; only emit explicit IDs
# when an existing tile is reused across or within the three credits screens.
old_mask=bytearray(420);old_refs=[];start_new=[];start_old=[];next_new=0
for i,ref in enumerate(refs):
 if i%1120==0:
  start_new.append(next_new);start_old.append(len(old_refs))
 if ref==next_new:
  next_new+=1
 else:
  assert ref<next_new,(i,ref,next_new)
  old_mask[i>>3]|=128>>(i&7);old_refs.append(ref)
assert next_new==len(unique) and len(start_new)==3
# 5 bits retain every original tile attribute including flip and priority.
attr5=bytearray(2101)
for i,v in enumerate(attrs):
 val=(v>>11)&31
 for j in range(5):
  if val&(1<<(4-j)):
   b=i*5+j;attr5[b>>3]|=128>>(b&7)
s=['#include <types.h>',
   'const u8 ending_old_mask[420]={'+','.join(map(str,old_mask))+'};',
   'const u16 ending_old_refs['+str(len(old_refs))+']={'+','.join(map(str,old_refs))+'};',
   'const u16 ending_start_new[3]={'+','.join(map(str,start_new))+'};',
   'const u16 ending_start_old[3]={'+','.join(map(str,start_old))+'};',
   'const u8 ending_attr5[2101]={'+','.join(map(str,attr5))+'};',
   'const u16 ending_pal[192]={'+','.join(map(str,palettes))+'};',
   'const u32 ending_tiles['+str(len(unique)*8)+']={'+','.join(hex(v) for t in unique for v in struct.unpack('>8I',t))+'};']
print('Credits metadata:',len(old_refs),'reused references; lossless compact index/attrs')

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
# Two user-approved Tile Palette Studio pictures, packed at native 320x224.
# ROM packs each 8x8 tile into a 4-colour local dictionary + 2bpp pixels;
# all 4 CRAM palettes and every spatial pixel are retained.
import base64,lzma,hashlib
lines=(src/'c7_user_compact_art.b85').read_text().splitlines()
assert lines[0]=='C7_USER_ART_2BPP_V1'
expected={'inter':'f7b5d9b849e952f7d8eaddbadcca45adbfa9077b2e245380d58549690517202b',
          'final':'fc7c280f7244a38e40a8f52e17ca1f9791d60000e096f864b75abe1e48b89b02'}
for name in ('inter','final'):
 j=lines.index('ASSET '+name)
 data=lzma.decompress(base64.b85decode(lines[j+1]))
 assert len(data)==20568 and hashlib.sha256(data).hexdigest()==expected[name]
 cp=struct.unpack('>64H',data[:128]);attrs2=data[128:408];tiles2=data[408:]
 s+=['const u16 '+name+'_pal[64]={'+','.join(map(str,cp))+'};',
     'const u8 '+name+'_tilepal2[280]={'+','.join(map(str,attrs2))+'};',
     'const u8 '+name+'_data[20160]={'+','.join(map(str,tiles2))+'};']
print('User intermission and ending: native 320x224, 4 CRAM palettes each')
(out/'ending_data.c').write_text('\n'.join(s)+'\n');print('Ending art:',len(unique),'unique tiles,',len(lines),'text lines')
