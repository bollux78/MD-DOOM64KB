import sys,ctypes as C,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));from libretro_runner import Emulator
from repack import repack
import argparse
a=argparse.ArgumentParser();a.add_argument('--build',type=Path,required=True);a.add_argument('--core',type=Path,required=True);opts=a.parse_args()
p=opts.build;e=Emulator(opts.core,p/'pipeline-static.bin');e.step(240,capture=True);e.screenshot().save(p/'pipeline-static.png')
vr=e.core.retro_dread_vram_word;got={}
expected=repack((p/'source.bin').read_bytes())
for base in [0x200,0x5c00]:
 data=b''.join(int(vr(base+i)).to_bytes(2,'little') for i in range(0,23040,2));got[hex(base)]={'equal':data==expected,'different_bytes':sum(a!=b for a,b in zip(data,expected))}
(p/'validation.json').write_text(json.dumps(got,indent=2)+'\n');print(got);e.close()
