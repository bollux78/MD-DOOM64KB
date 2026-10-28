#!/usr/bin/env python3
from pathlib import Path
import struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from gen_r81_font import generate
# Real Doom patch encoding, with a dark outline and bright letter face.
rows=['........','..###...','.#...#..','.#...#..','.#####..','.#...#..','.#...#..','........']
w=h=8;columns=[]
for x in range(w):columns.append(bytes([0,h,0]+[2 if rows[y][x]=='#' else 1 for y in range(h)]+[0,255]))
off=8+4*w;offsets=[]
for c in columns:offsets.append(off);off+=len(c)
patch=struct.pack('<4h',w,h,0,0)+struct.pack('<8I',*offsets)+b''.join(columns)
pal=bytearray(768);pal[3:6]=bytes([40,0,0]);pal[6:9]=bytes([191,32,0])
tiles,report=generate({'PLAYPAL':bytes(pal),'STCFN065':patch,'STCFN063':patch})
assert len(tiles)==96 and sum(len(t)*4 for t in tiles)==3072
assert not any(tiles[0]) and tiles[65-32]==tiles[97-32]
for y,line in enumerate(rows):
 for x,c in enumerate(line):assert ((tiles[65-32][y]>>(28-4*x))&15)==(15 if c=='#' else 0)
assert report[65-32]['scaled']==False
print('PASS original font decoder/mask: dark outline excluded, bright face preserved, 96 tiles, lowercase alias')
