#!/usr/bin/env python3
"""Own R22 four-pixel projection, palette and VRAM map constants."""
from pathlib import Path
import math,runpy
r=Path(__file__).resolve().parents[2]
g=runpy.run_path(str(r/'scripts/genpal.py'))
pp=g['load_playpal']();rgb=g['decode_subpal'](pp,0)
boxes=[list(range(256))]
while len(boxes)<14:
 b=max((b for b in boxes if len(b)>1),key=lambda b:max(max(rgb[i][c] for i in b)-min(rgb[i][c] for i in b) for c in range(3)))
 axis=max(range(3),key=lambda c:max(rgb[i][c] for i in b)-min(rgb[i][c] for i in b))
 boxes.remove(b);b.sort(key=lambda i:rgb[i][axis]);mid=len(b)//2;boxes.extend([b[:mid],b[mid:]])
reps=[]
for b in boxes:
 mean=tuple(sum(rgb[i][c] for i in b)//len(b) for c in range(3));reps.append(min(b,key=lambda i:g['dist2'](rgb[i],mean)))
reps.sort(key=lambda i:sum(rgb[i]))
words=[0]+[g['gen_color'](rgb[i]) for i in reps]+[0xeee]
prgb=list(map(g['gen_to_rgb'],words))
lookup=[min(range(16),key=lambda j:g['dist2'](rgb[i],prgb[j])) for i in range(256)]
cram=[]
for sub in range(14):
 colors=g['decode_subpal'](pp,sub);cram.append([0]+[g['gen_color'](colors[i]) for i in reps]+[0xeee])
(r/'src/r22_palette.h').write_text('/* Generated from Doom PLAYPAL: 14 representative colors + black/white. */\nstatic const uint8_t r22_color[256]={'+','.join(map(str,lookup))+'};\nstatic const uint16_t r22_cram[14][16]={\n'+',\n'.join('{'+','.join(map(str,row))+'}' for row in cram)+'};\n')
w=76;cx=w//2;v=[];raw=[]
for i in range(4096):
 t=int(math.tan((i-2048+0.5)*math.pi/4096)*65536)
 z=(cx*65536-cx*t+65535)//65536;raw.append(z);v.append(max(0,min(w,z)))
start=next(i for i,x in enumerate(v) if x<w)
xt=[(next(i for i,val in enumerate(raw) if val<=x)-2048)*8&65535 for x in range(w+1)]
xt[-1]=(-xt[0])&65535
(r/'src/r22_projection_max.h').write_text(f'#define VIEWANGLETOXMAX {start}\n')
(r/'src/r22_viewangletox.h').write_text(',\n'.join(','.join(map(str,v[i:i+32])) for i in range(start,3073,32)).rstrip(',')+'\n')
# Last chunk must stop at3073, matching the declared table bound.
a=v[start:3073];(r/'src/r22_viewangletox.h').write_text(',\n'.join(','.join(map(str,a[i:i+32])) for i in range(0,len(a),32))+'\n')
(r/'src/r22_xtoviewangle.h').write_text(','.join(map(str,xt))+'\n')
# Two 836-tile banks fit below relocated SGDK font at tile1696.
maps=[[16+bank*836+i for i in range(836)] for bank in range(2)]
(r/'src/r22_maps.h').write_text('/* Aligned to avoid the MD DMA128KiB source wrap within any row. */\nstatic const uint16_t r22_maps[2][836] __attribute__((aligned(4096)))={\n'+',\n'.join('{'+','.join(map(str,row))+'}' for row in maps)+'};\n')
print('R22: palette16, framebuffer76x44/1672B, VRAM banks16..1687, 77 projection entries')

(r/'src/r22_pair_lut.h').write_text('/* All256 packed pairs expanded to one8-pixel tile row. */\nstatic const uint32_t r22_pair_lut[256]={'+','.join(str(((p>>4)*0x11110000)|((p&15)*0x1111))+'u' for p in range(256))+'};\n')
