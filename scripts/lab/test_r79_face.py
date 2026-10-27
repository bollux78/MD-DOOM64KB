#!/usr/bin/env python3
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_hud_wad as G
from test_gen_hud_wad import synthetic_lumps
p=argparse.ArgumentParser();p.add_argument('--wad');args=p.parse_args()
lumps=G.read_iwad(Path(args.wad).read_bytes()) if args.wad else dict(synthetic_lumps())
if not args.wad:
    # Exercise artwork protruding into the requested two-pixel margin.
    lumps[G.FACE_NAMES[0]]=G.encode_patch([[153]*32 for _ in range(30)])
assets=G.build_assets(lumps);original=G.build_images(lumps)
protected=0
for fi,face in enumerate(assets['faces']):
 for y in range(32):
  for x in range(32):
   w=face[(y//8)*4+x//8][y%8];n=(w>>(28-4*(x%8)))&15
   edge=x<2 or x>=30;art=original['fmasks'][fi][y][x]
   assert (n==0)==(edge and not art),(fi,x,y,n)
   protected+=int(edge and art)
print('PASS R79 all 42 faces: 2px background margins transparent, interior black opaque, protruding face pixels preserved:',protected)
