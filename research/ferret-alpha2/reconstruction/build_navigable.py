from pathlib import Path
import argparse,subprocess,shutil,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--prefix',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);src=Path(__file__).resolve().parent
for n in ['navigation_boot.s','scene.ld','navigation.h','navigation_scene.c','navigation.c','navigation_runtime.c']:shutil.copy(src/n,a.out/n)
shutil.copy(a.assets/'navigation_data.c',a.out/'navigation_data.c')
for n in ['cram.bin','vsram.bin']:shutil.copy(a.capture/'first-published'/n,a.out/n)
vram=bytearray((a.capture/'first-published/vram.bin').read_bytes());vram[0x200:0xb600]=bytes(0xb400);(a.out/'vram.bin').write_bytes(vram)
reg=bytearray((a.capture/'first-published/vdp-registers.bin').read_bytes());reg[0]&=~16;reg[1]=4;(a.out/'registers.bin').write_bytes(reg)
def run(*cmd):
 try:return subprocess.check_output(list(cmd),cwd=a.out,text=True,stderr=subprocess.STDOUT)
 except subprocess.CalledProcessError as e:print(e.output);raise
run(a.prefix+'as','-m68000','--register-prefix-optional','navigation_boot.s','-o','navigation_boot.o')
for n in ['navigation_scene','navigation','navigation_runtime','navigation_data']:run(a.prefix+'gcc','-m68000','-O2','-ffreestanding','-fno-builtin','-fomit-frame-pointer','-fno-pie','-fno-asynchronous-unwind-tables','-c',n+'.c','-o',n+'.o')
run(a.prefix+'gcc','-m68000','-nostdlib','-Wl,-T,scene.ld','navigation_boot.o','navigation_scene.o','navigation.o','navigation_runtime.o','navigation_data.o','-lgcc','-o','navigation.elf')
run(a.prefix+'objcopy','-O','binary','navigation.elf','Ferret-Reconstrucao-Navegavel-v03.bin')
f=a.out/'Ferret-Reconstrucao-Navegavel-v03.bin';b=bytearray(f.read_bytes());b.extend(bytes((-len(b))%131072));b[0x1a4:0x1a8]=(len(b)-1).to_bytes(4,'big');b[0x18e:0x190]=(sum(int.from_bytes(b[i:i+2],'big') for i in range(512,len(b),2))&65535).to_bytes(2,'big');f.write_bytes(b)
(a.out/'symbols.txt').write_text(run(a.prefix+'nm','-S','navigation.elf'));(a.out/'build.json').write_text(json.dumps({'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'controls':'up/down move; left/right turn; A runs; Start resets spawn','limitations':'Experimental E1M1 geometry navigation; static HUD/weapon; no actors or game logic; visibility conditions enabled; original door logic not reconstructed.'},indent=2)+'\n');print(len(b),hashlib.sha256(b).hexdigest())
