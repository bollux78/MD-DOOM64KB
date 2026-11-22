from pathlib import Path
import argparse,ctypes as C,json
from libretro_runner import Emulator
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,required=True);p.add_argument('--build',type=Path,required=True);p.add_argument('--host-library',type=Path,required=True);a=p.parse_args();syms={}
for line in (a.build/'symbols.txt').read_text().splitlines():
 c=line.split()
 if len(c)==4:syms[c[3]]=int(c[0],16)&65535
info=json.loads((a.build/'build.json').read_text());assert info['hold_after_frames']==1
lib=C.CDLL(str(a.host_library.resolve()));buffer=(C.c_ubyte*11520)();lib.render_scene(buffer,info['initial_pose']);expected=bytes(buffer)
e=Emulator(a.core,a.build/'geometry.bin');e.step(600,capture=True)
def read(name,n):
 b=C.string_at(e.ram+syms[name],n);return b''.join(b[i:i+2][::-1] for i in range(0,n,2))
got=read('phase3_framebuffer',11520);result={'frames':int.from_bytes(read('phase3_frames',4),'big'),'pose':info['initial_pose'],'source_equals_host_C':got==expected,'different_bytes':sum(x!=y for x,y in zip(got,expected))};e.screenshot().save(a.build/'geometry.png');(a.build/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(result);assert result['frames']==1 and result['source_equals_host_C'];e.close()
