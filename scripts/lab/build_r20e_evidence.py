#!/usr/bin/env python3
"""Native semantic checks plus a real GCC15 MC68000 arithmetic/flat probe.
The raw probe is executed in Musashi by the orchestrating agent after download.
"""
import os,pathlib,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[2];os.chdir(root)
with tempfile.TemporaryDirectory() as tmp:
    exe=pathlib.Path(tmp)/"math"
    subprocess.run(["gcc","-O2","-std=c11","-iquote",str(root/"src"),"scripts/lab/test_r20e_math.c","-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
    print("PASS native M3: sine products, all divisors 1..2^24-1, boundaries and 2M random divisors",flush=True)
for test in ["test_r20e_scale.py","test_r20e_video.py"]:
    subprocess.run([sys.executable,"scripts/lab/"+test],check=True)
subprocess.run([sys.executable,"scripts/lab/gen_r20e_math_probe.py"],check=True)
gdk=pathlib.Path(os.path.expanduser(os.environ.get("DOOM_MD_GDK","~/mars/m68k-elf")))
gcc=gdk/"bin/m68k-elf-gcc";objcopy=gdk/"bin/m68k-elf-objcopy"
e=root/"dist/r20e/evidence"
libgcc=subprocess.check_output([str(gcc),"-m68000","-print-libgcc-file-name"],text=True).strip()
subprocess.run([str(gcc),"-m68000","-O3","-fno-web","-fno-gcse","-fno-tree-loop-ivcanon","-fomit-frame-pointer","-flto","-ffreestanding","-fno-builtin","-nostdlib","-Icompat","-Isrc",str(e/"math-boot.s"),str(e/"math-probe.c"),libgcc,"-Wl,-T,"+str(e/"math-probe.ld"),"-o",str(e/"math-probe.elf")],check=True)
subprocess.run([str(objcopy),"-O","binary","-j",".text",str(e/"math-probe.elf"),str(e/"math-probe.raw")],check=True)
mem=gdk/"inc/memory_base.h"
if mem.exists():(e/"sgdk-memory-base.txt").write_text(mem.read_text())
print("READY: actual m68k helper/R3 probe for external Musashi execution",flush=True)
