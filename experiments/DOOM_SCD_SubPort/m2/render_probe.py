#!/usr/bin/env python3
"""M2a: what does the R128 renderer need on the Sega CD sub-CPU?

Compiles every R128 source with the SUB defines (the S1d/S2e set: no SRAM block links, no R23
map memory, no R25 music windows, no R81 saves; R24 kept), then links with --gc-sections from
R_RenderPlayerView only (plus I_FinishUpdate separately) and reports, names and sizes only:
  - functions / const / bss of the renderer closure, largest objects;
  - unresolved symbols in that closure (what must be replaced on the sub);
  - which source files contribute.
Usage: render_probe.py TREE OUTDIR
"""
import collections, os, re, subprocess, sys
from pathlib import Path

tree, out = (Path(a).resolve() for a in sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
gdk = Path(os.environ.get("SGDK", str(Path.home() / "mars/m68k-elf")))
b = lambda t: str(gdk / "bin" / ("m68k-elf-" + t))
opt = (tree / "out/.render_options").read_text().split()
drop = ("DOOM_R22_SRAM_BLOCKLINKS", "DOOM_R23_MAPMEM", "DOOM_R25_MUSIC", "DOOM_R81_SAVE")
import shutil
# Variant 3: keep ALL R128 defines (R22/R23/R25 map memory included) but move the "cartridge SRAM"
# into sub PRG-RAM: same odd-lane layout, enable/disable become no-ops.
patched = out / "src-sram-in-ram"
if patched.exists(): shutil.rmtree(patched)
shutil.copytree(tree / "src", patched)
for f in patched.rglob("*"):
    if f.suffix not in (".c", ".h", ".inc"): continue
    t = f.read_text(errors="replace"); o = t
    t = t.replace("#define R22_SRAM_BASE 0x00200000UL", "#define R22_SRAM_BASE SCD_SRAM_BASE")
    t = t.replace("#define DOOM_SRAM_FIRST 0x0020F001UL", "#define DOOM_SRAM_FIRST (SCD_SRAM_BASE+0xF001UL)")
    t = t.replace("#define DOOM_SRAM_FIRST 0x00200001UL", "#define DOOM_SRAM_FIRST (SCD_SRAM_BASE+1UL)")
    t = t.replace("#define DOOM_SRAM_CONTROL 0x00A130F1UL", "#define DOOM_SRAM_CONTROL (SCD_SRAM_BASE+0x1FFFEUL)")
    t = t.replace("(*(volatile uint8_t*)0x00A130F1UL=1)", "((void)0)").replace("(*(volatile uint8_t*)0x00A130F1UL=0)", "((void)0)")
    if t != o: f.write_text(t); print("patched", f.name)
variants = {
    "sub-defines": [o for o in opt if o.startswith("-D") and not o.startswith(tuple("-D" + d for d in drop))],
    "sub-defines-norecip": [o for o in opt if o.startswith("-D") and not o.startswith(tuple("-D" + d for d in drop + ("DOOM_R12_RECIP",)))],
    "sram-in-ram": [o for o in opt if o.startswith("-D")] + ["-DSCD_SRAM_BASE=0x00060000UL"],
}
for label, defs in variants.items():
    w = out / label
    w.mkdir(exist_ok=True)
    cflags = ["-DSGDK_GCC", "-I.", "-I" + str(tree / "out"), "-isystem", str(gdk / "inc"), "-isystem", str(gdk / "lib"),
              "-m68000", "-O2", "-fno-builtin", "-ffreestanding", "-fomit-frame-pointer", "-fms-extensions",
              "-ffunction-sections", "-fdata-sections", "-std=gnu11", "-w",
              "-I" + str(patched if label == "sram-in-ram" else tree / "src"), "-I" + str(tree / "compat")] + defs
    srcroot = patched if label == "sram-in-ram" else tree / "src"
    objs, fails = [], []
    for src in sorted(p for p in srcroot.rglob("*") if p.suffix in (".c", ".s") and "boot" not in p.parts):
        obj = w / (src.relative_to(srcroot).as_posix().replace("/", "_") + ".o")
        cmd = [b("gcc")] + cflags + (["-x", "assembler-with-cpp", "-Wa,--register-prefix-optional,--bitwise-or"] if src.suffix == ".s" else []) + ["-c", str(src), "-o", str(obj)]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tree))
        (fails.append((src.name, next((l for l in r.stderr.splitlines() if "error" in l.lower()), "?")[-160:])) if r.returncode else objs.append(str(obj)))
    print("\n=== %s: %d defines, compiled %d, failed %d" % (label, len(defs), len(objs), len(fails)))
    for n, e in fails: print("  FAIL %-22s %s" % (n, e))
    rel = w / "all-r.o"
    subprocess.run([b("ld"), "-r", "-o", str(rel)] + objs, check=True)
    libgcc = subprocess.check_output([b("gcc"), "-m68000", "-print-libgcc-file-name"], text=True).strip()
    for root in ("R_RenderPlayerView", "I_FinishUpdate"):
        elf = w / (root + ".elf")
        r = subprocess.run([b("gcc"), "-m68000", "-nostdlib", "-Wl,--gc-sections", "-Wl,-e," + root, "-Wl,-u," + root,
                            "-Wl,--unresolved-symbols=ignore-all", "-Wl,-Ttext=0x6000", "-Wl,-Map," + str(w / (root + ".map")),
                            "-o", str(elf), str(rel), libgcc], capture_output=True, text=True)
        if r.returncode:
            print("  link from %s failed: %s" % (root, r.stderr[-300:])); continue
        cat, big = collections.Counter(), []
        for line in subprocess.check_output([b("nm"), "-S", "--size-sort", str(elf)], text=True).splitlines():
            f = line.split()
            if len(f) != 4: continue
            size, kind, name = int(f[1], 16), f[2], f[3]
            key = "WAD" if name.startswith("doom_iwad") else "funcs" if kind in "Tt" else "const" if kind in "RrDd" else "bss" if kind in "BbCc" else "other"
            cat[key] += size
            big.append((size, kind, name))
        und = sorted({l.split()[-1] for l in subprocess.check_output([b("nm"), "-u", str(elf)], text=True).splitlines() if l.strip()})
        # Unresolved names that are actually referenced from the kept closure (from the map's cross refs is
        # heavy); nm -u on the gc'd image lists the ones still needed.
        print("  closure from %s: %s" % (root, ", ".join("%s %.1f KiB" % (k, v / 1024) for k, v in cat.most_common())))
        print("    unresolved (%d): %s" % (len(und), " ".join(und)))
        print("    largest: " + "; ".join("%s %s %d" % (n, k, s) for s, k, n in sorted(big, reverse=True)[:18]))
        srcs = collections.Counter()
        for line in (w / (root + ".map")).read_text(errors="replace").splitlines():
            m = re.match(r"\s+\.(?:text|rodata|data|bss)\S*\s+0x[0-9a-f]+\s+0x([0-9a-f]+)\s+.*/([^/]+)\.o$", line)
            if m: srcs[m.group(2)] += int(m.group(1), 16)
        print("    by source: " + "; ".join("%s %.1fK" % (n, v / 1024) for n, v in srcs.most_common(14)))

# Who references the big tables (section = function with -ffunction-sections)?
w = out / "sram-in-ram"
targets = ("r91_joint", "r84_pixels", "r84_offsets", "r12_recip_table", "doom_iwad", "r79_map", "r77_h_comp_odd", "r76_l_comp_odd")
refs = collections.defaultdict(set)
for obj in sorted(w.glob("*.o")):
    if obj.name == "all-r.o": continue
    sec = None
    for line in subprocess.run([b("objdump"), "-r", str(obj)], capture_output=True, text=True).stdout.splitlines():
        m = re.match(r"RELOCATION RECORDS FOR \[(.+)\]:", line)
        if m: sec = m.group(1); continue
        for t in targets:
            if line.rstrip().endswith(t) or (" " + t + "+") in line or line.split()[-1:] == [t]:
                refs[t].add("%s:%s" % (obj.name.replace(".c.o", ""), sec))
print("\n=== references to big tables (object:section)")
for t in targets:
    print("  %s <- %s" % (t, ", ".join(sorted(refs[t])) or "-"))
