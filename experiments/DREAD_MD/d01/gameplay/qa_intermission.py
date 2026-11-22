from qa_support import *
import numpy as np
# Press E1M1's real exit switch. Do not force the exit flag.
g=fixture(0);g.put('cheat_god',1);i=w.find('E1M1');ld=w.idx(i+2);vs=w.idx(i+4)
for j in range(0,len(ld),14):
 l=struct.unpack_from('<7H',ld,j)
 if l[3]==11:break
ax,ay=struct.unpack_from('<hh',vs,l[0]*4);bx,by=struct.unpack_from('<hh',vs,l[1]*4);dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy)
x=(ax+bx)/2+dy/length*24;y=(ay+by)/2-dx/length*24
warp(g,x,y,math.degrees(math.atan2((ay+by)/2-y,(ax+bx)/2-x)));g.e.step(50);g.e.step(40,0);g.e.step(90,capture=True)
print('intermission',g.rd('intermission_active'),'map',g.rd('selected_map')+1,'secrets',g.rd('level_total_secrets'),flush=True);assert g.rd('intermission_active')==1 and g.rd('selected_map')==0;g.shot('intermission-hangar')
batches=[];BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
def callback(data,n):batches.append(C.string_at(data,n*4));return n
cb=BATCH(callback);g.e.core.retro_set_audio_sample_batch(cb);g.e.step(120,capture=True);a=np.frombuffer(b''.join(batches),np.int16).astype(float);print('intermission music RMS',float(np.sqrt(np.mean(a*a))),flush=True);assert np.max(np.abs(a))>100
# It must remain here until a new button, then load E1M2 with correct HUD/mode.
assert g.rd('selected_map')==0;g.press(1,220);print('after button',g.rd('selected_map')+1,'active',g.rd('intermission_active'),'mode',g.rd('mode'),flush=True);assert g.rd('selected_map')==1 and g.rd('intermission_active')==0;g.shot('after-intermission');g.e.close()
