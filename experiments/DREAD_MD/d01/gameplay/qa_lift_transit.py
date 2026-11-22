from qa_support import *
g=fixture(1);g.put('cheat_god',1)
for k in range(g.syms['actors'][1]//22):write(g,g.syms['actors'][0]+k*22+12,bytes([0,6]))
# E1M2 line 313 is a switch on the lift's south edge.
warp(g,-640,24,270);g.e.step(30);g.e.step(40,0)
a=g.syms['runtime_sectors'][0];stride=g.syms['runtime_sectors'][1]//(g.syms['floor_target'][1]//2)
for n in range(20):
 f=int.from_bytes(g.bytes(a+89*stride,2),'big',signed=True)
 if f<=24:break
 g.e.step(10)
print('lift lowered',f,'stride',stride,flush=True);g.e.step(35,4,capture=True);print('on lift',struct.unpack('>iihH',g.raw('view',12)),flush=True);g.shot('lift-entered');g.e.step(330,capture=True);print('lift raised',int.from_bytes(g.bytes(a+89*stride,2),'big',signed=True),struct.unpack('>iihH',g.raw('view',12)),flush=True);g.shot('lift-ridden');g.e.close()
