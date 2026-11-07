#!/usr/bin/env python3
"""S1d-Z4 actual R128 P_SetupLevel geometry-phase ROM, or Z5 full strict-link probe.

Usage: build_setup.py GENERATED_TREE S1B_OUT RAM_OBJECT_DIR PRIVATE_OUT [--full]
This modifies ONLY the disposable generated worktree. Nothing is written to
the main checkout or user-approved ROMs. All WAD/ROM objects stay private.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

if len(sys.argv) not in (5, 6) or (len(sys.argv)==6 and sys.argv[5]!="--full"):
    raise SystemExit("usage: build_setup.py TREE S1B_OUT RAM_OBJECTS OUT [--full]")
tree,s1b,ram,out=(Path(s).resolve() for s in sys.argv[1:5])
full=len(sys.argv)==6
here=Path(__file__).resolve().parent
common=here.parent
out.mkdir(parents=True,exist_ok=True)
objdir=out/"sub"
objdir.mkdir(exist_ok=True)
gdk=Path(os.environ.get("SGDK",str(Path.home()/"mars/m68k-elf")))
gcc=str(gdk/"bin/m68k-elf-gcc")
nm=str(gdk/"bin/m68k-elf-nm")
objcopy=str(gdk/"bin/m68k-elf-objcopy")
opt=(tree/"out/.render_options").read_text().split()
defs=[o for o in opt if o.startswith("-D") and not o.startswith(tuple(
    "-D"+d for d in ("DOOM_R22_SRAM_BLOCKLINKS","DOOM_R23_MAPMEM",
    "DOOM_R24_EPISODE","DOOM_R81_SAVE","DOOM_R25_MUSIC")))]
cflags=["-DSGDK_GCC","-DDOOM_R23_CPU_PROBE","-I.","-I"+str(tree/"out"),
    "-isystem",str(gdk/"inc"),"-isystem",str(gdk/"lib"),
    "-m68000","-O2","-fno-builtin","-ffreestanding",
    "-fomit-frame-pointer","-fms-extensions","-ffunction-sections",
    "-fdata-sections","-std=gnu11","-w","-I"+str(here),
    "-I"+str(common),"-I"+str(tree/"src"),"-I"+str(tree/"compat")]+defs

# Generated R128 source is compiled with original P_SetupLevel body,
# except two narrowly scoped changes in the GEOMETRY-ONLY experiment:
# (1) drop texture preload that exists purely for the MD renderer;
# (2) stop just after actual P_GroupLines, before thinker/item spawns.
p_setup=(tree/"src/p_setup.c").read_text()
if not full:
    anchor='#include "r24_romthings.h"'
    assert p_setup.count(anchor)==1,"p_setup include anchor changed"
    p_setup=p_setup.replace(anchor,anchor+'\n#define P_LoadTexture(t) ((void)0) /* sub no-render only */')
    anchor='    P_GroupLines();'
    assert p_setup.count(anchor)==1,"P_GroupLines anchor changed"
    p_setup=p_setup.replace(anchor,anchor+'''
    /* Z4: stop AFTER original geometry loader, BEFORE spawning gameplay.
       The function remains the actual source P_SetupLevel. */
    return;
''')
# No heavy sprintf on bare sub-CPU: equivalent E1M1..E1M9 label generation.
needle='sprintf(lumpname, "E1M%d", map);'
assert p_setup.count(needle)==1,"map label format changed"
p_setup=p_setup.replace(needle,
    "lumpname[0]='E'; lumpname[1]='1'; lumpname[2]='M'; "
    "lumpname[3]=(char)('0'+map); lumpname[4]=0;")
patched=objdir/"p_setup.c"
patched.write_text(p_setup)
parts=[]
for name,source in (("setup",here/"setup_sub_main.c"),
                     ("bsp",here/"setup_bsp_state.c"),
                     ("p_setup",patched)):
    obj=objdir/(name+".o")
    call=subprocess.run([gcc]+cflags+["-c",str(source),"-o",str(obj)],
                        cwd=tree,capture_output=True,text=True)
    if call.returncode:
        print("S1d",name,"C COMPILE FAIL\n"+call.stderr[-8000:],flush=True)
        raise SystemExit(1)
    parts.append(obj)
base=s1b/"sub"
kept=[base/name for name in ("boot.o","libc.o","scd_sub_transport.c.o",
                             "scd_sub_w_wad.c.o")]
kept += [ram/name for name in ("p_tick.o","g_game.o","z_zone.o","scd_sub_system.o")]
for obj in kept:
    if not obj.is_file(): raise SystemExit("Missing object: "+str(obj))
objs=[str(x) for x in kept+parts]
if full:
    for path in sorted(ram.glob("*.o")):
        if path.name not in ("p_setup.o","p_tick.o","g_game.o",
                            "z_zone.o","scd_sub_system.o",
                            "scd_sub_transport.o","scd_sub_w_wad.o"):
            objs.append(str(path))

libgcc=subprocess.check_output([gcc,"-m68000","-print-libgcc-file-name"],
                               text=True).strip()
elf=objdir/("full.elf" if full else "geometry.elf")
link=[gcc,"-m68000","-nostdlib","-Wl,--gc-sections",
      "-Wl,-e,subcpu_vectors","-Wl,-Ttext=0",
      "-Wl,-Map,"+str(objdir/"setup.map"),"-o",str(elf)]+objs+[libgcc]
p=subprocess.run(link,capture_output=True,text=True)
report=dict(phase="Z5 full P_SetupLevel STRICT diagnostic — not a ROM" if full
       else "Z4 actual P_SetupLevel geometry phase",linked=p.returncode==0,
       errors=p.stderr[-16000:],object_count=len(objs))
(out/"link_report.json").write_text(json.dumps(report,indent=2)+"\n")
print("S1d",("Z5" if full else "Z4"),"strict link:",
      "PASS" if p.returncode==0 else "FAIL", "objects",len(objs),flush=True)
if p.returncode:
    print(p.stderr[-10000:],flush=True)
    if full:
        print("Z5 is diagnostic only. No full-engine ROM was generated.",flush=True)
        raise SystemExit(0)
    raise SystemExit(1)
symbols={}
for row in subprocess.check_output([nm,str(elf)],text=True).splitlines():
    v=row.split()
    if len(v)==3:
        try: symbols[v[2]]=int(v[0],16)
        except ValueError: pass
for root in ("subcpu_vectors","P_SetupLevel","P_InitThinkers"):
    if root not in symbols: raise SystemExit("Missing linked runtime root: "+root)
if symbols["subcpu_vectors"]!=0: raise SystemExit("bad boot vector")
if symbols.get("_end",0)>=0x7E000: raise SystemExit("sub PRG-RAM end exceeds stack reserve")
binary=objdir/"setup.bin"
subprocess.run([objcopy,"-O","binary","-R",".bss",
                str(elf),str(binary)],check=True)
if binary.stat().st_size>128*1024:
    raise SystemExit("setup payload exceeds existing S1b single-window loader")
print("S1d linked sub image bytes",binary.stat().st_size,
      "RAM end",hex(symbols["_end"]),flush=True)
if full:
    print("Z5 strict link succeeded but boot/emulator has NOT been verified.",flush=True)
    raise SystemExit(0)

# Reuse trusted S1b boot and gameplay fallback, packaging private diagnostic ROM.
subprocess.run(["python3",str(common.parent/
    "DOOM_SCD_Bench03D_Transport/tools/make_sub_header.py"),
    str(binary),str(tree/"src/s1b_sub.h")],check=True)
md=(common/"s1b/s1b_md.c").read_text()
needle="for(u16 i=1;i<=3;i++)"
assert md.count(needle)==1
md=md.replace(needle,"for(u16 i=1;i<=9;i++)")
needle="    REPORT=r;"
assert md.count(needle)==1
md=md.replace(needle,
    "    r.reserved=(r.stage==5 || r.stage==6)?*(volatile const u16*)0xA12024:0;\n"
    +needle)
# S1b's 4-request check must be replaced for the E1M1 9-lump test.
needle="const bool pass=r.stage==5 && r.serviced==4"
assert md.count(needle)==1,"S1b acceptance predicate changed"
md=md.replace(needle,
    "const bool pass=r.reserved==0x5A5Du && r.stage==5 && r.serviced==10")
assert md.count("r.serviced==4")==0
assert md.count("r.serviced==10")==1
needle='VDP_drawText("S1B SUB WAD TRANSPORT",1,2);'
assert md.count(needle)==1
md=md.replace(needle,
    'VDP_drawText("S1D Z4 REAL P_SETUP GEOM",1,2);\n'
    '    VDP_drawText(r.reserved==0x5A5Du?"SETUP PASS":"SETUP FAIL",1,11);')
(tree/"src/s1b_md.c").write_text(md)
env=dict(os.environ,PATH=str(gdk/"bin")+":"+os.environ["PATH"])
subprocess.run(["make","GDK="+str(gdk),"PREFIX=m68k-elf-","JAVA=java",
                "EXTRA_FLAGS=-Isrc -Icompat -std=gnu11 "+" ".join(
                    o for o in opt if o.startswith("-D")),
                "LIBGCC="+libgcc+" -lgcc"],
               cwd=tree,env=env,check=True)
rom=out/"doom-md-scd-s1d-z4.bin"
linear=out/"linear.bin"
subprocess.run(["python3","scripts/lab/finish_r35_rom.py",
                "out/rom.bin",str(linear)],check=True,cwd=tree)
subprocess.run(["python3",str(common.parent/
    "DOOM_SCD_Bench03D_Transport/tools/mark_mode1.py"),
    str(linear),str(rom)],check=True)
subprocess.run(["python3",str(common.parent/
    "DOOM_SCD_03E/rom_identity.py"),str(rom)],check=True)
linear.unlink()
shutil.copyfile(tree/"out/release/rom.out",out/"doom-md-scd-s1d-z4.elf")
print("S1d Z4 private ROM:",rom,flush=True)
