from qa_support import *
g=v.Game(VARIANT);g.play();g.put('nactors',0);g.press(3,150);g.press(5);g.press(7);g.press(7);assert g.rd('mode')==4;g.press(3,180);g.put('bench_req',3);g.put('bench_done',3)
for i,pose in enumerate([(1536,-3600,45),(1536,-3600,90),(2200,-3370,180)]):
 warp(g,*pose);g.e.step(220,capture=True);g.shot('fullheight-sky-'+str(i))
 print('pose',pose,'mode',g.rd('mode'),'skyshift',g.rd('r_skyshift') if 'r_skyshift' in g.syms else None,'vints',g.rd('vints'),flush=True)
g.e.close()
