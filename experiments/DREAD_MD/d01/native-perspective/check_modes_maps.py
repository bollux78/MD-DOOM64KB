import sys,json
from pathlib import Path
import ctypes as C
import validation as v
results=[]
for name in sys.argv[1:]:
 g=v.Game(name);g.play();g.press(3,20)
 # Resolution row selected. Move from H40 to H32.
 g.press(7);assert g.rd('mode')==2
 g.press(5)
 for mode in [3,6,2]:
  g.press(7);assert g.rd('mode')==mode
  g.press(3,120);g.shot('mode-'+str(mode));results.append({'variant':name,'mode':mode,'height':g.rd('r_vh'),'width':g.rd('r_vw'),'hint_on':C.c_ubyte.from_address(g.e.ram+(g.syms['hint_on'][0]^1)).value,'framebuffer_bytes':g.rd('r_fbbytes')});g.press(3,20);g.press(5)
 g.e.close()
 for m in [1,7]:
  g=v.Game(name);g.play(m);g.e.step(180,4,capture=True);g.shot('map-'+str(m+1))
  assert g.rd('selected_map')==m
  results.append({'variant':name,'map':'E1M'+str(m+1),'player_view':g.raw('view',12).hex()});g.e.close()
print(json.dumps(results,indent=2))
(v.ROOT/'all-modes-maps.json').write_text(json.dumps(results,indent=2))
