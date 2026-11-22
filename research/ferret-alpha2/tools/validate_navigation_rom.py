from pathlib import Path
import sys,ctypes as C,json
sys.path.insert(0,str(Path(__file__).resolve().parent));from libretro_runner import Emulator
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True);parser.add_argument('--core',type=Path,required=True);parser.add_argument('--host-library',type=Path,required=True);args=parser.parse_args();p=args.build;syms={}
for line in (p/'symbols.txt').read_text().splitlines():
 c=line.split()
 if len(c)==4:syms[c[3]]=int(c[0],16)&65535
class Camera(C.Structure):_fields_=[(n,C.c_int16) for n in ['x','y','z','si','co','sky']]
lib=C.CDLL(str(args.host_library.resolve()));fb=(C.c_ubyte*11520)();e=Emulator(args.core,p/'Ferret-Reconstrucao-Navegavel-v03.bin')
def raw(name,n):
 b=C.string_at(e.ram+syms[name],n);return b''.join(b[i:i+2][::-1] for i in range(0,n,2))
def put(name,v):C.memmove(e.ram+syms[name],v.to_bytes(2,'big')[::-1],2)
rows=[]
for label,frames,key in [('spawn-audit',180,None),('walk-audit',240,4),('rotate-audit',90,6),('reverse-audit',120,5),('reset-audit',60,3),('back-wall-audit',600,5)]:
 put('navigation_debug_pause',0);e.step(frames,key,capture=True);put('navigation_debug_pause',1);e.step(90,capture=True)
 b=raw('navigation_camera',12);values=[int.from_bytes(b[i:i+2],'big',signed=True) for i in range(0,12,2)];camera=Camera(*values);cell=int.from_bytes(raw('navigation_cell',2),'big');lib.render_view(fb,C.byref(camera),cell);got=raw('navigation_framebuffer',11520);diff=sum(a!=b for a,b in zip(got,bytes(fb)));row={'label':label,'camera':values,'cell':cell,'framebuffer_equals_host':diff==0,'different_bytes':diff,'frame_count':int.from_bytes(raw('navigation_frames',4),'big')};rows.append(row);print(row);e.screenshot().save(p/(label+'.png'));assert diff==0
assert rows[1]['cell']!=rows[0]['cell'] and rows[2]['camera'][3:5]!=rows[1]['camera'][3:5]
assert rows[4]['camera'][:3]==rows[0]['camera'][:3]
assert -208*8<=rows[5]['camera'][1]<=-204*8
(p/'rom-validation.json').write_text(json.dumps(rows,indent=2)+'\n');e.close()
