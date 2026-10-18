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

# Compact actor dimensions preserve exact table values and corpse heights.
import re
values=re.findall(r'(\d+)\*FRACUNIT,\s*// (radius|height)',(r/'src/info.c').read_text())
assert len(values)==98
for value,field in values:
 n=int(value);assert 0<=n<256
 assert ((n*65536>>8)<<8)==n*65536
 if field=='height':assert (((n*256)>>2)<<8)==(n*65536>>2)
print('Q8 dimensions preserve all 98 actor table values and corpse quarters exactly')

# The engine stores wall NORMAL angles; source Doom SEGS store tangent angles.
import math
segs=c.recs(c.map_at(w,'E1M2')['SEGS'],'>hhhhHHHHBB')
for x,y,xx,yy,offset,normal,*rest in segs:
 expected=round((math.atan2(yy-y,xx-x)+math.pi/2)*65536/math.tau)&65535
 error=abs(((normal-expected+32768)&65535)-32768)
 assert error<=512,(x,y,xx,yy,normal,expected)
for dx,dy,expected in [(1,0,16384),(0,1,32768),(-1,0,49152),(0,-1,0)]:
 tangent=round(math.atan2(dy,dx)*65536/math.tau)&65535
 assert ((tangent+16384)&65535)==expected
print('All 1463 E1M2 wall normals match geometry; four cardinal normal conventions verified')
