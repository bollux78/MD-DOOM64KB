from qa_support import *
import numpy as np
# Four resolutions, exact cycle, without changing HUD dimensions.
g=v.Game(VARIANT);g.play();g.put('nactors',0);g.press(3,100);g.press(5);rs=[]
for expected in [(1,80,144),(9,80,72),(4,160,144),(0,160,72)]:
 g.press(7);actual=(g.rd('mode'),g.rd('r_vw'),g.rd('r_vh'));assert actual==expected,(actual,expected);g.shot('resolution-menu-'+str(actual[0]));g.press(3,100);g.e.step(90,capture=True);g.shot('resolution-'+str(actual[0]));rs.append(actual);g.press(3,100);g.press(5)
g.press(3);g.e.close();print('modes',rs,flush=True)
# Stable camera, active VBlank animation; check every frame for a black viewport.
g=fixture(0);g.put('nactors',0);g.put('owned_weapons',63);g.put('cheat_kfa',1);h=next(k for k in g.syms if k.startswith('hud.'));ha=g.syms[h][0];write(g,ha+6,struct.pack('>4H',200,50,50,200));reports=[]
for wpn in range(6):
 g.put('current_weapon',wpn);g.e.step(100,capture=True);before=g.bytes(ha+6,8);base=np.asarray(g.e.screenshot());count=int(np.count_nonzero(base[16:160]));minimum=count;frames=[]
 for n in range(100):
  g.e.step(1,1 if n<40 else None,capture=True);im=np.asarray(g.e.screenshot());minimum=min(minimum,int(np.count_nonzero(im[16:160])));
  if n in [10,20,50,99]:g.shot('weapon-'+str(wpn)+'-'+str(n))
 after=g.bytes(ha+6,8);ratio=minimum/max(count,1);assert ratio>.85,(wpn,ratio);assert before==after,(wpn,before.hex(),after.hex());reports.append({'weapon':wpn,'min_nonblack_ratio':ratio,'infinite_ammo':before==after})
print('weapon tests',json.dumps(reports),flush=True);g.e.close()
