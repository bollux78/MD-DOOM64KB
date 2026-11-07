#!/usr/bin/env python3
"""S1b: build the sub-CPU program from R128 engine objects (S0) and install the test into the R128 tree.
Usage: build.py TREE S0_OBJECT_DIR OUT_DIR"""
import os, shutil, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
common = here.parent
s1a = common / "s1a"
tree, objs, out = (Path(a).resolve() for a in sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
gdk = Path(os.environ.get("SGDK", str(Path.home() / "mars/m68k-elf")))
b = lambda t: str(gdk / "bin" / ("m68k-elf-" + t))
opts = (tree / "out/.render_options").read_text().split()
defs = [o for o in opts if o.startswith("-")]
cflags = ["-DSGDK_GCC", "-I.", "-I" + str(tree / "out"), "-isystem", str(gdk / "inc"), "-isystem", str(gdk / "lib"),
          "-m68000", "-O2", "-fomit-frame-pointer", "-fms-extensions", "-fno-builtin", "-ffreestanding",
          "-ffunction-sections", "-fdata-sections", "-std=gnu11", "-w",
          "-I" + str(here), "-I" + str(common), "-I" + str(tree / "src"), "-I" + str(tree / "src"), "-I" + str(tree / "compat")] + defs
w = out / "sub"
w.mkdir(exist_ok=True)
subprocess.run([b("as"), "-m68000", str(s1a / "sub_boot.s"), "-o", str(w / "boot.o")], check=True)
subprocess.run([b("gcc")] + cflags + ["-c", str(here / "sub_main.c"), "-o", str(w / "main.o")], check=True, cwd=str(tree))
subprocess.run([b("gcc"), "-m68000", "-O2", "-ffreestanding", "-fno-builtin", "-ffunction-sections", "-c", str(s1a / "sub_libc.c"), "-o", str(w / "libc.o")], check=True)
for name in ("scd_sub_transport.c","scd_sub_w_wad.c"):
    subprocess.run([b("gcc")] + cflags + ["-c",str(common / name),"-o",str(w / (name+".o"))],
                   check=True,cwd=str(tree))
libgcc = subprocess.check_output([b("gcc"), "-m68000", "-print-libgcc-file-name"], text=True).strip()
elf = w / "sub.elf"
engine = [str(w / (n+".o")) for n in ("scd_sub_transport.c","scd_sub_w_wad.c")]
subprocess.run([b("gcc"), "-m68000", "-nostdlib", "-Wl,--gc-sections", "-Wl,-e,subcpu_vectors", "-Wl,-Ttext=0",
                "-Wl,-Map," + str(w / "sub.map"), "-o", str(elf), str(w / "boot.o"), str(w / "main.o"), str(w / "libc.o")] + engine + [libgcc],
               check=True)
sym = {}
for l in subprocess.check_output([b("nm"), str(elf)], text=True).splitlines():
    f = l.split()
    if len(f) == 3: sym[f[2]] = int(f[0], 16)
assert sym["subcpu_vectors"] == 0, "vectors must be at address 0"
assert sym["_end"] < 0x7E000, "sub image + bss must leave room for the stack"
subprocess.run([b("objcopy"), "-O", "binary", "-R", ".bss", str(elf), str(w / "sub.bin")], check=True)
size = (w / "sub.bin").stat().st_size
assert size <= 128 * 1024, "S1b loader copies one 128 KiB PRG-RAM window"
print("S1b sub image: %d bytes, bss end 0x%X" % (size, sym["_end"]))
subprocess.run(["python3", str(common.parent / "DOOM_SCD_Bench03D_Transport/tools/make_sub_header.py"),
                str(w / "sub.bin"), str(tree / "src/s1b_sub.h")], check=True)
for n, source in (("s1b_md.c",here/"s1b_md.c"),("scd_md_server.c",common/"scd_md_server.c"),("scd_proto.h",common/"scd_proto.h")):
    shutil.copyfile(source,tree / "src" / n)
p = tree / "src/w_wad.c"
ws=p.read_text()
needle="const char __far* PUREFUNC W_GetNameForNum(int16_t num)"
assert ws.count(needle)==1
ws=ws.replace(needle,"uint16_t SCD_MdLumpCount(void) { const wadinfo_t *header=(const wadinfo_t *)&doom_iwad[0]; return (uint16_t)header->numlumps; }\n\n"+needle)
p.write_text(ws)
g = tree / "src/i_genesis.c"
s = g.read_text()
anchor = "\tD_DoomMain(argc, argv);"
assert s.count(anchor) == 1
s = s.replace(anchor, "\t{ void S1B_Test(void); S1B_Test(); }\n" + anchor)
g.write_text(s)
render = " ".join(defs)
env = dict(os.environ, PATH=str(gdk / "bin") + ":" + os.environ["PATH"])
subprocess.run(["make", "GDK=" + str(gdk), "PREFIX=m68k-elf-", "JAVA=java",
                "EXTRA_FLAGS=-Isrc -Icompat -std=gnu11 " + render, "LIBGCC=" + libgcc + " -lgcc"],
               check=True, cwd=str(tree), env=env)
rom = out / "doom-md-scd-s1b.bin"
subprocess.run(["python3", "scripts/lab/finish_r35_rom.py", "out/rom.bin", str(out / "linear.bin")], check=True, cwd=str(tree))
tools = common.parent
subprocess.run(["python3", str(tools / "DOOM_SCD_Bench03D_Transport/tools/mark_mode1.py"), str(out / "linear.bin"), str(rom)], check=True)
subprocess.run(["python3", str(tools / "DOOM_SCD_03E/rom_identity.py"), str(rom)], check=True)
(out / "linear.bin").unlink()
shutil.copyfile(tree / "out/release/rom.out", out / "doom-md-scd-s1b.elf")
print("S1b ROM:", rom)
