"""Build a static graphics-pipeline proof from a LOCAL capture, not Ferret code."""
from pathlib import Path
import argparse,subprocess,shutil,hashlib,json
p=argparse.ArgumentParser();p.add_argument('--capture',type=Path,required=True);p.add_argument('--prefix',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
src=Path(__file__).with_name('display.s');shutil.copy(src,a.out/'display.s')
for dst,src in {'vram.bin':'first-published/vram.bin','cram.bin':'first-published/cram.bin','vsram.bin':'first-published/vsram.bin','source.bin':'completed_source.bin'}.items():shutil.copy(a.capture/src,a.out/dst)
regs=bytearray((a.capture/'first-published/vdp-registers.bin').read_bytes());regs[0]&=~16;regs[1]=4;(a.out/'registers.bin').write_bytes(regs)
def run(*cmd):subprocess.run(list(cmd),cwd=a.out,check=True)
run(a.prefix+'as','-m68000','--register-prefix-optional','display.s','-o','display.o')
run(a.prefix+'ld','-Ttext=0','-e','_start','display.o','-o','display.elf')
run(a.prefix+'objcopy','-O','binary','display.elf','pipeline-static.bin')
rom=bytearray((a.out/'pipeline-static.bin').read_bytes());rom.extend(bytes((-len(rom))%131072));rom[0x1a4:0x1a8]=(len(rom)-1).to_bytes(4,'big');rom[0x18e:0x190]=(sum(int.from_bytes(rom[i:i+2],'big') for i in range(512,len(rom),2))&65535).to_bytes(2,'big');(a.out/'pipeline-static.bin').write_bytes(rom)
(a.out/'build.json').write_text(json.dumps({'size':len(rom),'sha256':hashlib.sha256(rom).hexdigest(),'kind':'static captured-scene pipeline proof; no reconstructed 3D'},indent=2)+'\n');print(len(rom),hashlib.sha256(rom).hexdigest())
