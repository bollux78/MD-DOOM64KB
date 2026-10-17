#!/usr/bin/env python3
import pathlib,os,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[2];os.chdir(root)
for test in ["test_r20g.py","gen_r20g_probe.py"]:subprocess.run([sys.executable,"scripts/lab/"+test],check=True)
gdk=pathlib.Path(os.path.expanduser(os.environ.get("DOOM_MD_GDK","~/mars/m68k-elf")));gcc=gdk/'bin/m68k-elf-gcc';objcopy=gdk/'bin/m68k-elf-objcopy';e=root/'dist/r20g/evidence'
libgcc=subprocess.check_output([str(gcc),"-m68000","-print-libgcc-file-name"],text=True).strip()
subprocess.run([str(gcc),"-m68000","-O3","-fno-web","-fno-gcse","-fno-tree-loop-ivcanon","-fomit-frame-pointer","-flto","-ffreestanding","-fno-builtin","-nostdlib","-Isrc",str(e/'probe-boot.s'),str(e/'render-probe.c'),"src/r20_reg_columns.s",libgcc,"-Wl,-T,"+str(e/'probe.ld'),"-o",str(e/'render-probe.elf')],check=True)
subprocess.run([str(objcopy),"-O","binary","-j",".text",str(e/'render-probe.elf'),str(e/'render-probe.raw')],check=True)
for name in ['memory_base.h','dma.h','config.h']:
 p=gdk/'inc'/name
 if p.exists():(e/('sgdk-'+name+'.txt')).write_text(p.read_text())
print('READY MC68000 R20g render probe; runtime emulation still required')
