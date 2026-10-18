#!/usr/bin/env python3
from pathlib import Path
import json,math,re
import convert_r24_episode as c
r=Path(__file__).resolve().parents[2];payload=json.loads((r/'assets/r24-episode.json').read_text());out,report=c.apply_all(payload,(r/'scripts/doom64.wad').read_bytes());wad=c.read_wad(out,True);d=dict(wad)
for num in range(1,10):
 m=c.map_at(wad,f'E1M{num}');records=c.recs(d[f'S{num}RTHING'],'>4H');rmap=[x[0] for x in c.recs(d[f'S{num}RMAP'],'>H')];things=c.recs(m['THINGS'],'>hhhbb');sides=c.recs(m['SIDEDEFS'],'>hBbbbB');lines=c.recs(m['LINEDEFS'],'>hhhhHhhHHhhhhhBbb');segs=c.recs(m['SEGS'],'>hhhhHHHHBB');subs=c.recs(m['SSECTORS'],'>HH');secs=d[f'S{num}SUBS'];assert len(rmap)==len(things)
 for i,rec in enumerate(records):assert rmap[rec[0]]==i+1 and rec[1]<len(subs)
 for prefix,key,groups in [('C','cell',len(c.recs(d[f'S{num}COFF'],'>H'))-1),('R','sector',len(m['SECTORS'])//12)]:
  offs=[x[0] for x in c.recs(d[f'S{num}{prefix}OFF'],'>H')];ix=[x[0] for x in c.recs(d[f'S{num}{prefix}IDX'],'>H')];assert sorted(ix)==list(range(len(records)))
  for group in range(groups):
   for index in ix[offs[group]:offs[group+1]]:assert (records[index][3] if prefix=='C' else secs[records[index][1]])==group
 if num not in [1,8]:
  for x,y,xx,yy,off,normal,side,line,front,back in segs:
   dx,dy=lines[line][5:7]
   if dx*(xx-x)+dy*(yy-y)<0:dx,dy=-dx,-dy
   expect=round((math.atan2(dy,dx)+math.pi/2)*65536/math.tau)&65535
   assert abs(((normal-expect+32768)&65535)-32768)<1024
 print(f'E1M{num}: {len(things)} things, {len(records)} ROM candidates, geometry and spatial indices verified')
# Independently compare state-machine tick evolution to the phase formula.
text=(r/'src/info.c').read_text();states={name:row.split(',') for row,name in re.findall(r'\{([^{}]+)\},?\s*// (S_\w+)',text)};blocks=re.findall(r'\{\s*// (MT_\w+)\n(.*?)\n  \}',text,re.S)
for definition,(_,body) in zip(c.definitions(),blocks):
 if not definition['static']:continue
 spawn=re.search(r'(S_\w+),\s*// spawnstate',body)[1];first=int(states[spawn][2]);period=definition['period']
 for delay in range(1,max(first,1)+1):
  real=spawn;remaining=delay if first>0 else -1
  for tick in range(1000):
   calc=spawn
   if first>0 and tick>=delay:
    elapsed=tick-delay;calc=states[spawn][4].strip()
    if period:elapsed%=period
    while int(states[calc][2])>0 and elapsed>=int(states[calc][2]):elapsed-=int(states[calc][2]);calc=states[calc][4].strip()
   assert real==calc,(definition['name'],tick,delay,real,calc)
   if remaining>0:
    remaining-=1
    if not remaining:real=states[real][4].strip();remaining=int(states[real][2])
print('ROM object animations exactly match sequential state ticks for every initial random phase')
