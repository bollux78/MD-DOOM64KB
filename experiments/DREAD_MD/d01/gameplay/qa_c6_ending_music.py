from qa_support import *
import numpy as np
g=fixture(7);g.put('cheat_god',1);g.put('exit_req',1);g.e.step(140,capture=True);assert g.rd('intermission_active')==1;g.press(1,180);g.shot('ending-dither');batches=[];BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
def cb(p,n):batches.append(C.string_at(p,n*4));return n
callback=BATCH(cb);g.e.core.retro_set_audio_sample_batch(callback);g.e.step(160,capture=True);a=np.frombuffer(b''.join(batches),np.int16).astype(float);print('ending audio RMS',float(np.sqrt((a*a).mean())));assert np.max(np.abs(a))>100
for n in range(3):g.press(1,100);g.shot('ending-credits-'+str(n))
g.press(1,200);g.shot('ending-return-title');g.e.close()
