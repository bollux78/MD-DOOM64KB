#!/usr/bin/env python3
"""S1d Z0: replace only the S1b sub image in an already built disposable R128 tree.

Run after s1b/build.py. Real sub-68000 Z_Init + allocation/free + remote WAD I/O.
The MD still plays R128 after START; this is NOT P_SetupLevel/G_Ticker on sub.
Usage: build_zone.py GENERATED_TREE PREVIOUS_S1B_OUT PRIVATE_OUTPUT
"""
import os, shutil, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
common = here.parent
tree, s1b, out = (Path(arg).resolve() for arg in sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
w = out / "sub"
w.mkdir(exist_ok=True)
gdk = Path(os.environ.get("SGDK", str(Path.home() / "mars/m68k-elf")))
b = lambda t: str(gdk / "bin" / ("m68k-elf-" + t))
options = (tree / "out/.render_options").read_text().split()
defs = [v for v in options if v.startswith("-D")]
cflags = ["-DSGDK_GCC", "-I.", "-I" + str(tree / "out"),
          "-isystem", str(gdk / "inc"), "-isystem", str(gdk / "lib"),
          "-m68000", "-O2", "-fomit-frame-pointer", "-fms-extensions",
          "-fno-builtin", "-ffreestanding", "-ffunction-sections",
          "-fdata-sections", "-std=gnu11", "-w", "-I" + str(here),
          "-I" + str(common), "-I" + str(tree / "src"),
          "-I" + str(tree / "compat")] + defs

base = s1b / "sub"
kept = [base / name for name in
        ("boot.o", "libc.o", "scd_sub_transport.c.o", "scd_sub_w_wad.c.o")]
for obj in kept:
    if not obj.is_file():
        raise SystemExit("Missing prerequisite S1b object: " + str(obj))

extra = [("zone_main", here / "zone_sub_main.c"),
         ("system", here / "scd_sub_system.c"),
         ("zone", tree / "src/z_zone.c")]
created = []
for name, source in extra:
    obj = w / (name + ".o")
    subprocess.run([b("gcc")] + cflags + ["-c", str(source), "-o", str(obj)],
                   check=True, cwd=str(tree))
    created.append(obj)

libgcc = subprocess.check_output(
    [b("gcc"), "-m68000", "-print-libgcc-file-name"], text=True).strip()
elf = w / "zone.elf"
link = [b("gcc"), "-m68000", "-nostdlib", "-Wl,--gc-sections",
        "-Wl,-e,subcpu_vectors", "-Wl,-Ttext=0",
        "-Wl,-Map," + str(w / "zone.map"),
        "-o", str(elf)] + [str(p) for p in kept + created] + [libgcc]
subprocess.run(link, check=True)
symbols = {}
for row in subprocess.check_output([b("nm"), str(elf)], text=True).splitlines():
    fields = row.split()
    if len(fields) == 3:
        try:
            symbols[fields[2]] = int(fields[0], 16)
        except ValueError:
            pass
assert symbols["subcpu_vectors"] == 0
assert symbols["_end"] < 0x7E000, "S1d Z0 PRG-RAM exceeds safety margin"
binary = w / "zone.bin"
subprocess.run([b("objcopy"), "-O", "binary", "-R", ".bss",
                str(elf), str(binary)], check=True)
assert binary.stat().st_size <= 128 * 1024, "S1b single-window loader limit"
print("S1d Z0 payload:", binary.stat().st_size,
      "BSS end:", hex(symbols["_end"]), flush=True)

subprocess.run(["python3", str(common.parent / "DOOM_SCD_Bench03D_Transport/tools/make_sub_header.py"),
                str(binary), str(tree / "src/s1b_sub.h")], check=True)
# Modify only a disposable generated worktree to expose a unique real-zone marker.
source = tree / "src/s1b_md.c"
md = source.read_text()
assert md.count("    REPORT=r;") == 1, "S1b diagnostic anchor changed"
md = md.replace("    REPORT=r;", "    r.reserved=(r.stage==5)?*(volatile const u16*)0xA12024:0;\n    REPORT=r;")
assert md.count("const bool pass=r.stage==5") == 1
md = md.replace("const bool pass=r.stage==5",
                "const bool pass=r.reserved==0x5A1Du && r.stage==5")
assert md.count('VDP_drawText("S1B SUB WAD TRANSPORT",1,2);') == 1
md = md.replace('VDP_drawText("S1B SUB WAD TRANSPORT",1,2);',
                'VDP_drawText("S1D Z0 Z_INIT + WAD",1,2);\n'
                '    VDP_drawText(r.reserved==0x5A1Du?"ZONE PASS":"ZONE FAIL",1,11);')
source.write_text(md)
# This also rebuilds the header-dependent s1b_md.o with the new sub image.
env = dict(os.environ, PATH=str(gdk / "bin") + ":" + os.environ["PATH"])
subprocess.run(["make", "GDK=" + str(gdk), "PREFIX=m68k-elf-", "JAVA=java",
                "EXTRA_FLAGS=-Isrc -Icompat -std=gnu11 " + " ".join(defs),
                "LIBGCC=" + libgcc + " -lgcc"],
               cwd=str(tree), env=env, check=True)
rom = out / "doom-md-scd-s1d-z0.bin"
linear = out / "linear.bin"
subprocess.run(["python3", "scripts/lab/finish_r35_rom.py",
                "out/rom.bin", str(linear)], check=True, cwd=str(tree))
subprocess.run(["python3", str(common.parent / "DOOM_SCD_Bench03D_Transport/tools/mark_mode1.py"),
                str(linear), str(rom)], check=True)
subprocess.run(["python3", str(common.parent / "DOOM_SCD_03E/rom_identity.py"),
                str(rom)], check=True)
linear.unlink()
shutil.copyfile(tree / "out/release/rom.out", out / "doom-md-scd-s1d-z0.elf")
print("S1d Z0 private ROM:", rom, flush=True)
