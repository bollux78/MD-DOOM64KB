from qa_support import *
from PIL import Image
import numpy as np
# Warm reset must restore title scrolling and disable row duplication.
g=v.Game(VARIANT);g.play();g.e.step(90,6);g.e.core.retro_reset();g.e.step(150,capture=True);g.press(3);g.shot('warm-reset-menu');g.press(5);g.press(1);g.shot('warm-reset-levels');g.e.close()
# Six ready frames, plus per-VBlank shotgun animation captured as a contact sheet.
g=fixture(0);g.put('nactors',0);g.put('owned_weapons',63)
h=next(k for k in g.syms if k.startswith('hud.'));write(g,g.syms[h][0]+6,struct.pack('>4H',200,50,50,200))
for weapon in range(6):
 g.put('current_weapon',weapon);g.e.step(90,capture=True);g.shot('ready-'+str(weapon))
 # Drive the animation via real fire so VRAM and SAT follow the same path as console.
 g.e.step(40,1);g.e.step(90,capture=True);g.shot('after-shot-'+str(weapon))
g.put('current_weapon',2);g.e.step(90);g.e.step(1,1)
for _ in range(90):
 g.e.step(1,1)
 if g.rd('weapon_last')==9:break
g.e.step(1);captures=[];trace=[]
for k in range(75):
 g.e.step(1,capture=True);trace.append((k,g.rd('weapon_last'),g.rd('weapon_pending'),g.rd('displayed_tint',1)))
 if k%3==0:captures.append(g.e.screenshot().resize((640,448),Image.Resampling.NEAREST))
contact=Image.new('RGB',(640*5,448*5));
for i,im in enumerate(captures):contact.paste(im,((i%5)*640,(i//5)*448))
contact.save(v.ROOT/'shots'/f'{VARIANT}-shotgun-contact.png');print('shotgun timeline',trace,flush=True);assert all(x[3]!=1 for x in trace),'weapon caused scene flash'
# Return option really goes to the opening; START still just resumes.
g.put('bench_req',0);g.press(3)
for _ in range(6):g.press(5)
g.shot('return-entry');g.press(1,180);g.shot('returned-opening');g.e.close()
