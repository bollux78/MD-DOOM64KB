from qa_support import *
g=v.Game(VARIANT);g.play()
# Isolate video/menu transitions from combat/death; sprite lists remain loaded.
g.put('nactors',0)
results=[]
for widthbit in [0,2]:
 g.press(3,200)
 if (g.rd('mode')&2)!=widthbit:g.press(7)
 g.press(5)
 for detail in [1,4,0]:
  g.press(7);assert g.rd('mode')==(widthbit|detail),(g.rd('mode'),widthbit|detail)
  g.press(3,200);v0=g.rd('vints');g.e.step(120,capture=True);assert g.rd('vints')!=v0,'VDP callback stopped (possible exception)'
  g.shot('detail-'+str(widthbit|detail));results.append({'mode':g.rd('mode'),'width':g.rd('r_vw'),'height':g.rd('r_vh'),'framebuffer_bytes':g.rd('r_fbbytes')})
  g.press(3,200);g.press(5)
 # Back to gameplay before opening the resolution row in the next pass.
 g.press(3,200)
g.e.close();print(json.dumps(results,indent=2));(v.ROOT/'video-results.json').write_text(json.dumps(results,indent=2))
