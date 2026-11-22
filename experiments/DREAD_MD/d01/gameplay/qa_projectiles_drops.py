from qa_support import *
g=v.Game(VARIANT);g.play();g.put('invuln',1800)
hud=next(n for n,(off,size) in g.syms.items() if n.startswith('hud.') and size==28);h=g.syms[hud][0]
# Resolve the RAM projectile symbol; render.c also has a static function called proj.
for line in subprocess.check_output([v.NM,'-S',v.ROOT/VARIANT/'EPISODE.elf'],text=True).splitlines():
 a=line.split()
 if len(a)==4 and a[3]=='proj' and a[2].lower()=='b':projoff=int(a[0],16)&65535
write(g,h+6,struct.pack('>4H',100,30,20,0));g.put('owned_weapons',63);g.put('current_weapon',4)
states=set()
for frame in range(300):
 g.e.step(1,1,capture=True)
 for i in range(8):
  p=g.bytes(projoff+i*24,24)
  if p[20]==3:states.add(p[21])
g.shot('rocket-live');result=[{'case':'rocket_live','states_seen':sorted(states),'flight_seen':0 in states,'explosion_seen':1 in states}];g.e.close()
# Kill a one-HP sergeant using the real fire button, then collect its dropped weapon.
g=v.Game(VARIANT);g.play(2);g.put('invuln',1800);actors=g.raw('actors');n=g.rd('nactors');target=next(i for i in range(n) if actors[i*22+12]==1)
write(g,g.syms['actors'][0]+target*22+10,b'\0\1')
for angle in [0,90,180,270]:
 a=g.raw('actors')[target*22:target*22+22];x,y=struct.unpack_from('>ii',a);x/=65536;y/=65536
 warp(g,x-math.cos(math.radians(angle))*48,y-math.sin(math.radians(angle))*48,angle);g.e.step(100,1,capture=True)
 a=g.raw('actors')[target*22:target*22+22]
 if a[13]>=4:break
x,y=struct.unpack_from('>ii',a);warp(g,x/65536,y/65536);g.e.step(90,capture=True);g.shot('sergeant-drop')
result.append({'case':'sergeant_drop','death_state':a[13],'owned_after_pickup':g.rd('owned_weapons'),'shotgun_received':bool(g.rd('owned_weapons')&4)});g.e.close()
print(json.dumps(result,indent=2));(v.ROOT/'projectiles-drops-results.json').write_text(json.dumps(result,indent=2))
