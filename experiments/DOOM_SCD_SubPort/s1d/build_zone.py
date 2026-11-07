#!/usr/bin/env python3
"""S1d Z0/Z1: replace the S1b sub image in a disposable R128 tree.

Run after s1b/build.py. Real sub-68000 Z_Init + allocation/free + remote WAD I/O.
The MD still plays R128 after START; this is NOT P_SetupLevel/G_Ticker on sub.
Usage: build_zone.py TREE S1B_OUT PRIVATE_OUT [--map|--resident|--construct]
"""
import os, shutil, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
common = here.parent
args = sys.argv[1:]
if len(args) not in (3, 4) or (len(args)==4 and args[3] not in ("--map","--resident","--construct")):
    raise SystemExit("usage: build_zone.py TREE S1B_OUT PRIVATE_OUT [--map|--resident|--construct]")
variant = args[3] if len(args)==4 else ""
map_mode = variant in ("--map","--resident","--construct")
live_mode = variant in ("--resident","--construct")
construct_mode = variant == "--construct"
tree, s1b, out = (Path(arg).resolve() for arg in args[:3])
out.mkdir(parents=True, exist_ok=True)
w = out / "sub"
w.mkdir(exist_ok=True)
gdk = Path(os.environ.get("SGDK", str(Path.home() / "mars/m68k-elf")))
b = lambda t: str(gdk / "bin" / ("m68k-elf-" + t))
options = (tree / "out/.render_options").read_text().split()
defs = [v for v in options if v.startswith("-D")]
# Preserve approved Mega Drive flags; only new sub builds use direct PRG-RAM layouts.
sub_defs = defs if not live_mode else [v for v in defs if not v.startswith(tuple(
    "-D"+d for d in ("DOOM_R22_SRAM_BLOCKLINKS","DOOM_R23_MAPMEM",
                  "DOOM_R24_EPISODE","DOOM_R81_SAVE","DOOM_R25_MUSIC")))]
if construct_mode: sub_defs += ["-DSCD_Z3_CONSTRUCT"]
cflags = ["-DSGDK_GCC", "-I.", "-I" + str(tree / "out"),
          "-isystem", str(gdk / "inc"), "-isystem", str(gdk / "lib"),
          "-m68000", "-O2", "-fomit-frame-pointer", "-fms-extensions",
          "-fno-builtin", "-ffreestanding", "-ffunction-sections",
          "-fdata-sections", "-std=gnu11", "-w", "-I" + str(here),
          "-I" + str(common), "-I" + str(tree / "src"),
          "-I" + str(tree / "compat")] + sub_defs

base = s1b / "sub"
kept = [base / name for name in
        ("boot.o", "libc.o", "scd_sub_transport.c.o", "scd_sub_w_wad.c.o")]
for obj in kept:
    if not obj.is_file():
        raise SystemExit("Missing prerequisite S1b object: " + str(obj))

extra = [("zone_main", here / ("resident_sub_main.c" if live_mode else "map_sub_main.c" if map_mode else "zone_sub_main.c")),
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
# Both Z0 and Z1 run against the same disposable generated work tree.
# Always start from pristine S1b source, not a previous diagnostic patch.
md = (common / "s1b" / "s1b_md.c").read_text()
if map_mode:
    original = "for(u16 i=1;i<=3;i++)"
    assert md.count(original) == 1, "S1b checksum loop changed"
    md = md.replace(original, "for(u16 i=1;i<=9;i++)")
marker = ("0x5A4Du" if construct_mode else "0x5A3Du" if live_mode else
          "0x5A2Du" if map_mode else "0x5A1Du")
title = ("S1D Z3 LIVE GEOMETRY" if construct_mode else "S1D Z2 RESIDENT MAP" if live_mode else
         "S1D Z1 E1M1 MAP LUMPS" if map_mode else "S1D Z0 Z_INIT + WAD")
assert md.count("    REPORT=r;") == 1, "S1b diagnostic anchor changed"
md = md.replace("    REPORT=r;", "    r.reserved=(r.stage==5 || r.stage==6)?*(volatile const u16*)0xA12024:0;\n    REPORT=r;")
# Replace the WHOLE request-count comparison, not just the stage prefix.
# S1b expects 4 (DIR + 3 lumps); Z1/Z2/Z3 expect 10 (DIR + 9).
needle = "const bool pass=r.stage==5 && r.serviced==4"
assert md.count(needle) == 1, "S1b acceptance predicate changed"
md = md.replace(needle,
    "const bool pass=r.reserved==" + marker +
    " && r.stage==5 && r.serviced==" + ("10" if map_mode else "4"))
assert md.count("r.serviced==4") == (0 if map_mode else 1)
assert md.count("r.serviced==10") == (1 if map_mode else 0)
assert md.count('VDP_drawText("S1B SUB WAD TRANSPORT",1,2);') == 1
md = md.replace('VDP_drawText("S1B SUB WAD TRANSPORT",1,2);',
                'VDP_drawText("' + title + '",1,2);\n'
                '    VDP_drawText(r.reserved==' + marker +
                '?"' + ('MAP PASS' if map_mode else 'ZONE PASS') +
                '":"' + ('MAP FAIL' if map_mode else 'ZONE FAIL') +
                '",1,11);')
source.write_text(md)
# This also rebuilds the header-dependent s1b_md.o with the new sub image.
env = dict(os.environ, PATH=str(gdk / "bin") + ":" + os.environ["PATH"])
subprocess.run(["make", "GDK=" + str(gdk), "PREFIX=m68k-elf-", "JAVA=java",
                "EXTRA_FLAGS=-Isrc -Icompat -std=gnu11 " + " ".join(defs),
                "LIBGCC=" + libgcc + " -lgcc"],
               cwd=str(tree), env=env, check=True)
name = ("doom-md-scd-s1d-z3" if construct_mode else "doom-md-scd-s1d-z2" if live_mode else
        "doom-md-scd-s1d-z1" if map_mode else "doom-md-scd-s1d-z0")
rom = out / (name + ".bin")
linear = out / "linear.bin"
subprocess.run(["python3", "scripts/lab/finish_r35_rom.py",
                "out/rom.bin", str(linear)], check=True, cwd=str(tree))
subprocess.run(["python3", str(common.parent / "DOOM_SCD_Bench03D_Transport/tools/mark_mode1.py"),
                str(linear), str(rom)], check=True)
subprocess.run(["python3", str(common.parent / "DOOM_SCD_03E/rom_identity.py"),
                str(rom)], check=True)
linear.unlink()
shutil.copyfile(tree / "out/release/rom.out", out / (name + ".elf"))
print("S1d " + ("Z3" if construct_mode else "Z2" if live_mode else "Z1" if map_mode else "Z0")+" ROM:", rom, flush=True)
