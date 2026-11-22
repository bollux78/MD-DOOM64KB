from pathlib import Path
import sys,ctypes as C,json
sys.path.insert(0,str(Path(__file__).resolve().parent));from libretro_runner import Emulator
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True);parser.add_argument('--core',type=Path,required=True);args=parser.parse_args();p=args.build;syms={}
for line in (p/'symbols.txt').read_text().splitlines():
 c=line.split()
 if len(c)==4:syms[c[3]]=int(c[0],16)&65535
print({k:hex(v) for k,v in syms.items() if k.startswith('navigation_') and not k.endswith('update')})
e=Emulator(args.core,p/'Ferret-Reconstrucao-Navegavel-v03.bin')
def raw(name,n):
 b=C.string_at(e.ram+syms[name],n);return b''.join(b[i:i+2][::-1] for i in range(0,n,2))
def put(name,v):C.memmove(e.ram+syms[name],v.to_bytes(2,'big')[::-1],2)
def state():
 b=raw('navigation_camera',12);c=[int.from_bytes(b[i:i+2],'big',signed=True) for i in range(0,12,2)];return dict(camera=c,cell=int.from_bytes(raw('navigation_cell',2),'big'),angle=int.from_bytes(raw('navigation_angle',2),'big'),frames=int.from_bytes(raw('navigation_frames',4),'big'),vblanks=int.from_bytes(raw('navigation_vblanks',2),'big'),buttons=int.from_bytes(raw('navigation_buttons',2),'big'))
rows=[]
for label,n,key in [('spawn',180,None),('forward',300,4),('left',90,6),('forward-turned',180,4),('right',90,7),('back',120,5),('reset',60,3)]:
 e.step(n,key,capture=True);s=state();s['label']=label;rows.append(s);print(label,s);e.screenshot().save(p/(label+'.png'))
(p/'navigation-input-test.json').write_text(json.dumps(rows,indent=2)+'\n');e.close()
