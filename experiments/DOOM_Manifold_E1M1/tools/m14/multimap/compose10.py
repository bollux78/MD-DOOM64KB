import subprocess, struct, os
os.chdir('/tmp/c10'); T="/home/claude/mars/m68k-elf/bin/m68k-elf-"; BANK=0x80000
MAPS=[("E1M1","E1M1  HANGAR"),("E1M2","E1M2  NUCLEAR PLANT"),("E1M4","E1M4  COMMAND CONTROL"),("E1M5","E1M5  PHOBOS LAB"),("E1M9","E1M9  MILITARY BASE")]
h=['#define LAYOUT_PER_MAP','#define NSLOT 4','#define MAP_ENTRY 0x00080200','#define MAP_COUNT 5','struct map_entry { const char *name; unsigned char bank; };','static const struct map_entry maps[] = {']
imgs=[]
for i,(m,l) in enumerate(MAPS):
    d=open("/tmp/m12/mm_%s/out/release/rom.bin"%m,"rb").read(); assert len(d)<=4*BANK
    imgs.append(d+b"\xff"*(4*BANK-len(d))); h.append('  {"%s", %d},'%(l,1+4*i))
h.append('};'); h.append('static const unsigned long bank_expect[5][4][8] = {')
for im in imgs:
    h.append('  {')
    for sl in range(4):
        h.append('    {'+','.join('0x%08XUL'%struct.unpack(">I",im[sl*BANK+k*0x10000+0x1230:sl*BANK+k*0x10000+0x1234])[0] for k in range(8))+'},')
    h.append('  },')
h.append('};'); open("maps.h","w").write("\n".join(h)+"\n")
subprocess.check_call(["python3","gen_assets.py"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
subprocess.check_call([T+"as","-m68000","crt0.s","-o","crt0.o"])
for f in("menu","assets"): subprocess.check_call([T+"gcc","-m68000","-Os","-ffreestanding","-fno-pic","-nostdlib","-c",f+".c","-o",f+".o"])
subprocess.check_call([T+"ld","-T","menu.ld","crt0.o","menu.o","assets.o","-o","menu.elf"]); subprocess.check_call([T+"objcopy","-O","binary","menu.elf","menu.bin"])
m=open("menu.bin","rb").read(); assert len(m)<=BANK
open("/home/claude/outputs/claudio-manifold-doom-MENU-5-FASES-10MB-MONSTROS.bin","wb").write(m+b"\xff"*(BANK-len(m))+b"".join(imgs)); print(len(m))
