from qa_support import *
def line_fixture(g,mapid,sp):
 i=w.find('E1M'+str(mapid+1));ld=w.idx(i+2);verts=w.idx(i+4);sides=w.idx(i+3)
 for j in range(0,len(ld),14):
  l=struct.unpack_from('<7H',ld,j)
  if l[3]!=sp:continue
  ax,ay=struct.unpack_from('<hh',verts,l[0]*4);bx,by=struct.unpack_from('<hh',verts,l[1]*4);dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy)
  x=(ax+bx)/2+dy/length*24;y=(ay+by)/2-dx/length*24;angle=math.degrees(math.atan2((ay+by)/2-y,(ax+bx)/2-x))
  sec=struct.unpack_from('<H',sides,l[6]*30+28)[0];return (x,y,angle),sec
results=[]
for sp,typ in [(26,5),(27,6),(28,13)]:
 g=fixture(5);pose,sec=line_fixture(g,5,sp);warp(g,*pose);g.e.step(40);g.e.step(40,0);g.e.step(20)
 before=int.from_bytes(g.raw('ceil_target')[sec*2:sec*2+2],'big',signed=True)
 keys=[t for t in things(5) if t[3]==typ and t[4]&2 and not t[4]&16];assert keys
 warp(g,keys[0][0],keys[0][1]);g.e.step(80);got=g.rd('player_keys')
 warp(g,*pose);g.e.step(40);g.e.step(40,0);g.e.step(20,capture=True)
 after=int.from_bytes(g.raw('ceil_target')[sec*2:sec*2+2],'big',signed=True)
 results.append({'case':'key_door','special':sp,'key_type':typ,'keys_after_pickup':got,'locked_target':before,'unlocked_target':after,'pass':after>before and bool(got)})
 g.shot('key-door-'+str(sp));g.e.close()
# Controls and all weapon frame uploads, with fixture ammunition.
g=fixture(0);hud=next(n for n,(off,size) in g.syms.items() if n.startswith('hud.') and size==28);hudoff=g.syms[hud][0]
g.put('owned_weapons',63)
for weapon in range(6):
 write(g,hudoff+6,struct.pack('>4H',100,30,20,0));g.put('current_weapon',weapon)
 g.e.step(140,1,capture=True);g.shot('fire-'+str(weapon))
 results.append({'case':'weapon','weapon':weapon,'pending_frame':g.rd('weapon_pending'),'weapon_tile_position':g.rd('weapon_pos'),'ammo':list(struct.unpack('>4H',g.bytes(hudoff+6,8)))})
 g.e.step(180)
# Test C+A through two simultaneously held libretro buttons.
old=g.rd('current_weapon');g.e.pad={8,1}
for _ in range(50):g.e.core.retro_run()
g.e.step(40,capture=True);results.append({'case':'cycle_C_A','before':old,'after':g.rd('current_weapon'),'pass':g.rd('current_weapon')!=old});g.e.close()
# Boss-special and ending logic (fixture kills, not a claim of playing the entire map).
g=fixture(7);n=g.rd('nactors');a=g.raw('actors');stride=g.syms['actors'][1]//int(Path('dread-gameplay-cache/E1M8/mapcounts.h').read_text().split('MAP_NACTORS ')[1].split()[0]) if False else 22
bosses=0
for i in range(n):
 if a[i*stride+12]==6:
  bosses+=1;write(g,g.syms['actors'][0]+i*stride+10,b'\0\0'+bytes([6,4]))
g.e.step(80)
results.append({'case':'baron_fixture','barons':bosses,'boss_done':g.rd('boss_done')})
i=w.find('E1M8');sectors=w.idx(i+8);sides=w.idx(i+3);ld=w.idx(i+2);verts=w.idx(i+4)
endsects=[j//26 for j in range(0,len(sectors),26) if struct.unpack_from('<h',sectors,j+22)[0]==11]
for j in range(0,len(ld),14):
 l=struct.unpack_from('<7H',ld,j)
 if l[5]==65535:continue
 sec=struct.unpack_from('<H',sides,l[5]*30+28)[0]
 if sec not in endsects:continue
 ax,ay=struct.unpack_from('<hh',verts,l[0]*4);bx,by=struct.unpack_from('<hh',verts,l[1]*4);dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy)
 warp(g,(ax+bx)/2+dy/length*8,(ay+by)/2-dx/length*8);break
hud=next(n for n,(off,size) in g.syms.items() if n.startswith('hud.') and size==28);write(g,g.syms[hud][0],struct.pack('>H',20))
g.e.step(600,capture=True);g.shot('episode-end');v0=g.rd('vints');g.e.step(30);results.append({'case':'end_fixture','vint_callback_stopped':g.rd('vints')==v0});
for label in ['end-id','end-project','end-md2','end-return-title']:
 g.press(1,80);g.shot(label)
results.append({'case':'end_returns_opening','map':g.rd('selected_map'),'vints_restarted':g.rd('vints')>0});g.e.close()
print(json.dumps(results,indent=2));(v.ROOT/'gameplay-more-results.json').write_text(json.dumps(results,indent=2))
