#!/usr/bin/env python3
"""S0: compile the R128 All engine for the Sega CD sub-CPU (no SGDK library) and report.

Input: a finished R128 All build work tree (generated headers + out/.render_options).
Output (stdout, public-safe: names and sizes only):
  - per-file compile result;
  - undefined external symbols after a relocatable link, grouped (SGDK / libc / hardware / other);
  - sizes after a --gc-sections link from main(): functions vs const data, largest objects,
    with the embedded WAD and music reported separately (they stay on the MD / ROM server).
Usage: s0_report.py WORKTREE OUTDIR
"""
import collections, os, re, subprocess, sys
from pathlib import Path

work, out = map(Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
tc = Path(os.environ.get("M68K_BIN", str(Path.home() / "mars/m68k-elf/bin")))
gcc, ld, nm = (str(tc / ("m68k-elf-" + t)) for t in ("gcc", "ld", "nm"))
opts = (work / "out/.render_options").read_text().split()
defs = [o for o in opts if o.startswith("-")]
sgdk = work / "vendor/sgdk"
cflags = ["-m68000", "-O3", "-fno-web", "-fno-gcse", "-fomit-frame-pointer", "-fms-extensions", "-fno-builtin",
          "-ffunction-sections", "-fdata-sections", "-std=gnu11", "-w",
          "-I" + str(work / "src"), "-I" + str(work / "compat"), "-I" + str(sgdk / "inc"), "-I" + str(sgdk / "res"),
          "-I" + str(work / "out"), "-I" + str(work / "res"), "-I" + str(work)] + defs
objs, fails = [], []
srcs = sorted(p for p in (work / "src").rglob("*") if p.suffix in (".c", ".s") and "boot" not in p.parts)
for src in srcs:
    obj = out / (src.relative_to(work / "src").as_posix().replace("/", "_") + ".o")
    cmd = [gcc] + cflags + (["-x", "assembler-with-cpp"] if src.suffix == ".s" else []) + ["-c", str(src), "-o", str(obj)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        fails.append((src.name, (r.stderr.strip().splitlines() or ["?"])[-1][:160]))
    else:
        objs.append(str(obj))
print("S0 defines:", len(defs), "| sources:", len(srcs), "| compiled:", len(objs), "| failed:", len(fails))
for name, err in fails:
    print("  FAIL %-24s %s" % (name, err))

rel = out / "engine-r.o"
subprocess.run([ld, "-r", "-o", str(rel)] + objs, check=True)
undef = sorted({l.split()[-1] for l in subprocess.check_output([nm, "-u", str(rel)], text=True).splitlines() if l.strip()})
groups = collections.defaultdict(list)
for s in undef:
    if re.match(r"_?(VDP_|SYS_|DMA_|Z80_|XGM|JOY_|PAL_|SPR_|TIM_|MEM_|SND_|BMP_|KLog|getTick|getTime|vint|hint|vtimer|intToStr|uintToStr|waitMs|waitTick|setRandomSeed|random$)", s):
        groups["SGDK (vira comando ao MD ou camada nova no sub)"].append(s)
    elif re.match(r"_?(mem|str|sprintf|vsprintf|printf|abs|labs|qsort|toupper|tolower|isdigit|isalpha|isspace|atoi)", s):
        groups["libc (implementar no sub)"].append(s)
    elif s.startswith(("__", "_ffs")):
        groups["libgcc (resolve no link)"].append(s)
    else:
        groups["outros (dados/funções de plataforma a examinar)"].append(s)
print("\nundefined after relocatable link: %d" % len(undef))
for g, names in groups.items():
    print("  %s: %d" % (g, len(names)))
    print("    " + " ".join(names))

libgcc = subprocess.check_output([gcc, "-m68000", "-print-libgcc-file-name"], text=True).strip()
elf = out / "engine-gc.elf"
r = subprocess.run([gcc, "-m68000", "-nostdlib", "-Wl,--gc-sections", "-Wl,-e,main", "-Wl,-u,main",
                    "-Wl,--unresolved-symbols=ignore-all", "-Wl,-Ttext=0x6000", "-o", str(elf), str(rel), libgcc],
                   capture_output=True, text=True)
if r.returncode:
    print("gc link failed:", r.stderr[-400:]); sys.exit(1)
cat, big = collections.Counter(), []
for line in subprocess.check_output([nm, "-S", "--size-sort", str(elf)], text=True).splitlines():
    f = line.split()
    if len(f) != 4: continue
    size, kind, name = int(f[1], 16), f[2], f[3]
    if name.startswith("doom_iwad"): key = "WAD (fica na ROM / servidor do MD)"
    elif name.startswith(("bgm_", "pcm_", "xgm", "stop_xgm", "z80_", "smp_")): key = "música/som (fica no MD)"
    elif kind in "Tt": key = "funções"
    elif kind in "RrDd": key = "dados const/iniciados"
    elif kind in "BbCc": key = "bss"
    else: key = "outros"
    cat[key] += size
    if kind in "RrDdBbCc" and not name.startswith("doom_iwad"): big.append((size, kind, name))
print("\nsizes after --gc-sections from main():")
for k, v in cat.most_common(): print("  %-34s %9d bytes %7.1f KiB" % (k, v, v / 1024))
print("largest data/bss objects:")
for size, kind, name in sorted(big, reverse=True)[:30]: print("  %8d %s %s" % (size, kind, name))
