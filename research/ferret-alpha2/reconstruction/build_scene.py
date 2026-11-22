from pathlib import Path
import argparse,subprocess,shutil,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--prefix',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--hold',type=int,default=0);p.add_argument('--pose',type=int,default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);src=Path(__file__).resolve().parent
for n in ['boot.s','scene.ld','scene.h','scene.c','runtime.c']:shutil.copy(src/n,a.out/n)
shutil.copy(a.assets/'data.c',a.out/'data.c')
for n in ['cram.bin','vsram.bin']:shutil.copy(a.capture/'first-published'/n,a.out/n)
vram=bytearray((a.capture/'first-published/vram.bin').read_bytes());vram[0x200:0xb600]=bytes(0xb400);(a.out/'vram.bin').write_bytes(vram)
reg=bytearray((a.capture/'first-published/vdp-registers.bin').read_bytes());reg[0]&=~16;reg[1]=4;(a.out/'registers.bin').write_bytes(reg)
def run(*cmd):return subprocess.check_output(list(cmd),cwd=a.out,text=True,stderr=subprocess.STDOUT)
run(a.prefix+'as','-m68000','--register-prefix-optional','boot.s','-o','boot.o')
for n in ['scene','runtime','data']:run(a.prefix+'gcc','-m68000','-O2','-ffreestanding','-fno-builtin','-fomit-frame-pointer','-fno-pie','-fno-asynchronous-unwind-tables',f'-DHOLD_AFTER={a.hold}',f'-DINITIAL_POSE={a.pose}','-c',n+'.c','-o',n+'.o')
run(a.prefix+'gcc','-m68000','-nostdlib','-Wl,-T,scene.ld','boot.o','scene.o','runtime.o','data.o','-lgcc','-o','geometry.elf')
run(a.prefix+'objcopy','-O','binary','geometry.elf','geometry.bin')
b=bytearray((a.out/'geometry.bin').read_bytes());b.extend(bytes((-len(b))%131072));b[0x1a4:0x1a8]=(len(b)-1).to_bytes(4,'big');b[0x18e:0x190]=(sum(int.from_bytes(b[i:i+2],'big') for i in range(512,len(b),2))&65535).to_bytes(2,'big');(a.out/'geometry.bin').write_bytes(b)
symbols=run(a.prefix+'nm','-S','geometry.elf');(a.out/'symbols.txt').write_text(symbols)
(a.out/'build.json').write_text(json.dumps({'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'hold_after_frames':a.hold,'initial_pose':a.pose,'limitations':'Spawn-cell walls from geometry; no actors; pose-matched sky; captured static HUD/weapon; 16 diagnostic camera poses, not navigation.'},indent=2)+'\n');print(len(b),hashlib.sha256(b).hexdigest())
