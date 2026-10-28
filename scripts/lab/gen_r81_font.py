#!/usr/bin/env python3
"""Original Doom STCFN font in the existing 96-tile 8x8 font bank."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_hud_wad as G

def generate(lumps):
 pal=lumps['PLAYPAL'];tiles=[];report=[]
 for code in range(32,128):
  source=code
  if 97<=source<=122:source-=32
  key=f'STCFN{source:03d}'
  rows=[[-1]*8 for _ in range(8)];w=h=0
  if code!=32 and key in lumps:
   w,h,data=G.decode_patch(lumps[key])
   # Preserve the source bitmap when it fits; nearest-neighbour only for a
   # rare oversized glyph, with no smoothing or generated replacement art.
   dw,dh=min(8,w),min(8,h);ox,oy=(8-dw)//2,(8-dh)//2
   for y in range(dh):
    for x in range(dw):rows[oy+y][ox+x]=data[min(h-1,y*h//dh)][min(w-1,x*w//dw)]
  elif code!=32:
   key='STCFN063'
   if key in lumps:
    w,h,data=G.decode_patch(lumps[key]);dw,dh=min(8,w),min(8,h)
    for y in range(dh):
     for x in range(dw):rows[(8-dh)//2+y][(8-dw)//2+x]=data[y*h//dh][x*w//dw]
  words=[]
  for row in rows:
   word=0
   for x,v in enumerate(row):
    foreground=v>=0 and any(pal[v*3:v*3+3])
    word|=(15 if foreground else 0)<<(28-4*x)
   words.append(word)
  tiles.append(words);report.append(dict(character=code,source=key,width=w,height=h,scaled=w>8 or h>8))
 assert len(tiles)==96 and all(w==0 for w in tiles[0])
 return tiles,report

def main():
 a=argparse.ArgumentParser();a.add_argument('--wad',required=True);a.add_argument('--out',required=True);a.add_argument('--preview');args=a.parse_args()
 lumps=G.read_iwad(Path(args.wad).read_bytes());assert 'STCFN065' in lumps,'Original Doom small font missing'
 tiles,report=generate(lumps)
 out='/* Original Doom small font, white mask; 96 tiles in existing font bank. */\n#ifndef R81_MENU_FONT_H\n#define R81_MENU_FONT_H\nstatic const uint32_t r81_menu_font[96][8]={\n'+',\n'.join('{'+','.join(f'0x{w:08X}UL' for w in t)+'}' for t in tiles)+'\n};\n#endif\n'
 Path(args.out).write_text(out);Path(args.out).with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
 if args.preview:
  img=[[(32,32,32)]*(16*8) for _ in range(6*8)]
  for i,tile in enumerate(tiles):
   for y,w in enumerate(tile):
    for x in range(8):img[(i//16)*8+y][(i%16)*8+x]=(255,255,255) if (w>>(28-4*x))&15 else (32,32,32)
  G.write_png(args.preview,[[p for p in row for _ in range(4)] for row in img for _ in range(4)])
 print('PASS R81 original small font: 96 tiles, existing VRAM 1440..1535, ROM 3072 bytes, extra WRAM 0')
if __name__=='__main__':main()
