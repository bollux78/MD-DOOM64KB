#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_hud_wad as G
from test_gen_hud_wad import synthetic_lumps
assets=G.build_assets(dict(synthetic_lumps()))
for face in assets['faces']:
 for y in range(32):
  for x in range(32):
   w=face[(y//8)*4+x//8][y%8];n=(w>>(28-4*(x%8)))&15
   assert (n==0)==(x<2 or x>=30),(x,y,n)
print('PASS R79 all 42 face frames: exactly 2px transparent on each side, all interior black remains opaque')
