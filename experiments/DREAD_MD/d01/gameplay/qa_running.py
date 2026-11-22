from qa_support import *
rs=[]
for run in [False,True]:
 g=fixture(0);g.put('nactors',0);warp(g,1056,-3616,90);g.e.step(50);start=struct.unpack('>iihH',g.raw('view',12));buttons=[4,0] if run else [4]
 for n in range(180):
  g.e.pad=set(buttons);g.e.core.retro_run();end=struct.unpack('>iihH',g.raw('view',12))
  if end[:2]!=start[:2]:break
 g.e.step(10);end=struct.unpack('>iihH',g.raw('view',12))
 d=math.hypot((end[0]-start[0])/65536,(end[1]-start[1])/65536);rs.append(d);g.e.close()
print('walk, run, ratio',rs,rs[1]/rs[0]);assert 1.8<rs[1]/rs[0]<2.2
