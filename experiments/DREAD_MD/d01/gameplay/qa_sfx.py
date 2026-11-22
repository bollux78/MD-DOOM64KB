from qa_support import *
import wave
import numpy as np
g=v.Game(VARIANT);g.play()
# Turn music off using the in-game option; XGM2 remains loaded for effects.
g.press(3)
for _ in range(3):g.press(5)
g.press(7);g.press(3);g.put('bench_req',3);g.put('bench_done',3);g.e.step(120)
batches=[]
BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
def callback(data,n):batches.append(C.string_at(data,n*4));return n
cb=BATCH(callback);g.e.core.retro_set_audio_sample_batch(cb)
g.e.step(40);silent=np.frombuffer(b''.join(batches),np.int16).astype(float);batches.clear()
g.e.step(100,1);g.e.step(60);sound=b''.join(batches);samples=np.frombuffer(sound,np.int16).astype(float)
r={'music_on':g.rd('music_on'),'baseline_rms':float(np.sqrt((silent**2).mean())),'fire_rms':float(np.sqrt((samples**2).mean())),'fire_peak':float(np.max(np.abs(samples))),'sample_pairs':len(samples)//2}
with wave.open(str(v.ROOT/'pistol-sfx.wav'),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(44100);f.writeframes(sound)
(v.ROOT/'sfx-results.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));g.e.close()
