from pathlib import Path
import sys,ctypes as C,json,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent));from libretro_runner import Emulator
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True);parser.add_argument('--core',type=Path,required=True);args=parser.parse_args();p=args.build;syms={}
for line in (p/'symbols.txt').read_text().splitlines():
 c=line.split()
 if len(c)==4:syms[c[3]]=int(c[0],16)&65535

def rd(e,name,n):
 b=C.string_at(e.ram+syms[name],n);return int.from_bytes(b''.join(b[i:i+2][::-1] for i in range(0,n,2)),'big')
e=Emulator(args.core,p/'Ferret-Reconstrucao-Navegavel-v03.bin');e.step(180);last=rd(e,'navigation_frames',4);times=[]
for i in range(1500):
 e.step(1);n=rd(e,'navigation_frames',4)
 if n!=last:times.append(i);last=n
intervals=np.diff(times);res={'video_frames':1500,'presentations':len(times),'fps_60hz':60*len(intervals)/int(intervals.sum()),'interval_histogram':{str(k):int(v) for k,v in zip(*np.unique(intervals,return_counts=True))},'scene':'actual BSP-selected spawn cell 131; no input; no actors; static overlay','sram':False,'sega_cd':False};(p/'benchmark.json').write_text(json.dumps(res,indent=2)+'\n');print(res);e.close()
