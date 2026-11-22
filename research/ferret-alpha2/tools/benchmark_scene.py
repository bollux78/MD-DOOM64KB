from pathlib import Path
import sys,ctypes as C,json,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent));from libretro_runner import Emulator
import argparse
a=argparse.ArgumentParser();a.add_argument('--build',type=Path,required=True);a.add_argument('--core',type=Path,required=True);opt=a.parse_args();p=opt.build;symbols={}
for l in (p/'symbols.txt').read_text().splitlines():
 c=l.split()
 if len(c)==4:symbols[c[3]]=int(c[0],16)&65535
e=Emulator(opt.core,p/'geometry.bin');e.step(180)
def frames():
 b=C.string_at(e.ram+symbols['phase3_frames'],4);return int.from_bytes(b[1::-1]+b[3:1:-1],'big')
last=frames();times=[]
for t in range(1500):
 e.step(1,capture=True);n=frames()
 if n!=last:times.append(t);last=n
if len(times)>1:
 d=np.diff(times);res={'presentations':len(times),'video_frames':1500,'fps_nominal_60hz':60*len(d)/int(d.sum()),'interval_video_frames_histogram':{str(k):int(v) for k,v in zip(*np.unique(d,return_counts=True))},'camera':0,'actors':False,'hud':'static captured overlay','sky':'fixed first view','method':'phase3_frames increments after full CPU pixel and name-table publication; no SRAM/SegaCD'}
 print(res);(p/'benchmark.json').write_text(json.dumps(res,indent=2)+'\n')
e.screenshot().save(p/'geometry-live.png');e.close()
