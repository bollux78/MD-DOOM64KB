from qa_support import *
# Test pickups via the game's collision/subsector collection path, not ownership writes.
g=fixture(0)
for typ in [2001,2005,5,6,13]:
 candidates=[t for t in things(0) if t[3]==typ and t[4]&2 and not t[4]&16]
 if not candidates:continue
 t=candidates[0];warp(g,t[0],t[1]);g.e.step(80,capture=True)
 results.append({'case':'pickup','type':typ,'owned':g.rd('owned_weapons'),'keys':g.rd('player_keys'),'weapon':g.rd('current_weapon')})
 g.shot('pickup-'+str(typ))
g.e.close()
# Real use button B (libretro B=0). Every regular exit and the secret route.
for mapid,sp in [(0,11),(1,11),(2,11),(2,51),(3,11),(4,11),(5,11),(6,11),(8,11)]:
 g=fixture(mapid);i=w.find('E1M'+str(mapid+1));ld=w.idx(i+2);verts=w.idx(i+4)
 candidates=[struct.unpack_from('<7H',ld,j) for j in range(0,len(ld),14) if struct.unpack_from('<7H',ld,j)[3]==sp]
 success=False
 for l in candidates:
  ax,ay=struct.unpack_from('<hh',verts,l[0]*4);bx,by=struct.unpack_from('<hh',verts,l[1]*4);dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy)
  for side in [1,-1]:
   x=(ax+bx)/2+side*dy/length*24;y=(ay+by)/2-side*dx/length*24;angle=math.degrees(math.atan2((ay+by)/2-y,(ax+bx)/2-x))
   warp(g,x,y,angle);g.e.step(40);g.e.step(40,0);g.e.step(240,capture=True)
   if 'intermission_active' in g.syms and g.rd('intermission_active'):g.press(1,240)
   if g.rd('selected_map')!=mapid:success=True;break
  if success:break
 target=8 if sp==51 else 3 if mapid==8 else mapid+1
 results.append({'case':'exit_button','map':mapid+1,'special':sp,'actual_next':g.rd('selected_map')+1,'expected_next':target+1,'pass':g.rd('selected_map')==target})
 g.shot('exit-'+str(mapid+1)+'-'+str(sp));g.e.close()
print(json.dumps(results,indent=2));(v.ROOT/'gameplay-results.json').write_text(json.dumps(results,indent=2))
