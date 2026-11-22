from qa_support import *
results=[]
for choice in range(4):
 g=v.Game(VARIANT);g.play();g.put('nactors',0)
 if choice:
  g.press(3,100);g.press(5)
  for n in range(choice):g.press(7)
  g.press(3,100)
 v0=g.rd('vints');g.put('bench_req',1);g.put('bench_done',0)
 for tick in range(20000):
  g.e.step(1)
  if g.rd('bench_done')>=1:break
 frames=g.rd('bench_frames',4);vbl=(g.rd('vints')-v0)&65535;r={'mode':g.rd('mode'),'width':g.rd('r_vw'),'height':g.rd('r_vh'),'frames':frames,'vblanks':vbl,'fps':frames*60/vbl};results.append(r);print(json.dumps(r),flush=True);g.e.close()
