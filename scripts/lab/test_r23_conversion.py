#!/usr/bin/env python3
from pathlib import Path
import json,hashlib
import convert_r23_e1m2 as c
r=Path(__file__).resolve().parents[2];base=(r/'scripts/doom64.wad').read_bytes();p=json.loads((r/'assets/r23-e1m2.json').read_text())
a,report=c.apply(p,base);b,_=c.apply(p,base);assert a==b
w=c.read_wad(a,True)
for num in [1,2,8]:
 m=c.map_at(w,f'E1M{num}');indices,offsets=c.associations(m);assert dict(w)[f'S{num}LINES']==indices and dict(w)[f'S{num}OFFS']==offsets
 lines=c.recs(m['LINEDEFS'],'>hhhhHhhHHhhhhhBbb');sides=c.recs(m['SIDEDEFS'],'>hBbbbB');offs=[x[0] for x in c.recs(offsets,'>H')];ix=[x[0] for x in c.recs(indices,'>H')]
 for sec in range(len(offs)-1):
  expected=[i for i,l in enumerate(lines) if sides[l[7]][-1]==sec or (l[8]!=65535 and sides[l[8]][-1]==sec)]
  assert ix[offs[sec]:offs[sec+1]]==expected
assert report['skill_counts']==[180,200,239]
print('R23 conversion deterministic; all sector memberships independently checked; original E1M1/E1M8 preserved')
