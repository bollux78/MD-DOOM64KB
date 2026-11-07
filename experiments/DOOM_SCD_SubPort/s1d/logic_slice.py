#!/usr/bin/env python3
"""S1d preflight: compile a logic-only R128 slice for the Sega CD sub CPU.

Not the S1d runtime. Avoids the MD/SRAM/video definitions and computes the
actual engine subset link footprint and undefined dependencies. CLI:
    logic_slice.py GENERATED_R128_TREE OUT_DIR
"""
import json, os, re, subprocess, sys
from pathlib import Path

work, out = [Path(p).resolve() for p in sys.argv[1:]]
out.mkdir(parents=True, exist_ok=True)
tc = Path(os.environ.get("M68K_BIN", str(Path.home() / "mars/m68k-elf/bin")))
gcc = str(tc / "m68k-elf-gcc")
nm = str(tc / "m68k-elf-nm")
size = str(tc / "m68k-elf-size")
opts = (work / "out/.render_options").read_text().split()
defines = [v for v in opts if v.startswith("-D") and not any(
    v.startswith("-D" + d) for d in (
        "DOOM_R25_MUSIC",
        "DOOM_R12_RECIP_LUT", "DOOM_R29_XGM2"))]
sgdk = Path(os.environ.get("SGDK", str(Path.home() / "mars/m68k-elf")))
cflags = ["-DSGDK_GCC", "-I.", "-I" + str(work / "out"),
          "-isystem", str(sgdk / "inc"), "-isystem", str(sgdk / "lib"),
          "-m68000", "-O2", "-fno-builtin", "-fomit-frame-pointer",
          "-fms-extensions", "-ffreestanding", "-ffunction-sections",
          "-fdata-sections", "-std=gnu11", "-w",
          "-I" + str(work / "src"), "-I" + str(work / "compat")] + defines

# This is deliberately the simulation core, not a complete game binary.
names = ["d_items", "g_game", "info", "m_random", "p_doors", "p_enemy",
         "p_enemy2", "p_floor", "p_inter", "p_lights", "p_map",
         "p_maputl", "p_mobj", "p_plats", "p_pspr", "p_setup",
         "p_sight", "p_spec", "p_switch", "p_telept", "p_tick",
         "p_user", "r22_blocklinks", "r23_mapmem", "r24_romthings",
         "tables", "z_bmallo", "z_zone"]
objects, failures = [], []
for name in names:
    source = work / "src" / (name + ".c")
    if not source.is_file():
        failures.append({"source": name, "error": "missing file"})
        continue
    obj = out / (name + ".o")
    p = subprocess.run([gcc] + cflags + ["-c", str(source), "-o", str(obj)],
                       cwd=work, capture_output=True, text=True)
    if p.returncode:
        failures.append({"source": name, "error": p.stderr[-1600:]})
    else:
        objects.append(str(obj))
report = {"phase": "S1d logic-only dependency preflight — NOT an executable",
          "compiled": len(objects), "requested": len(names), "compile_failures": failures,
          "excluded_md_features": ["MUSIC", "RECIP_LUT", "XGM2"],\n          "known_blocker": "R128 R81/R119/R24 structures depend on R23_MAPMEM; retaining R23 in this probe, NOT valid sub hardware configuration"}
if not failures:
    reloc = out / "logic-slice.o"
    p = subprocess.run([gcc, "-m68000", "-nostdlib", "-Wl,-r",
                        "-o", str(reloc)] + objects,
                       capture_output=True, text=True)
    report["reloc_link_ok"] = not p.returncode
    report["reloc_link_error"] = p.stderr[-2000:]
    if not p.returncode:
        sym = subprocess.check_output([nm, str(reloc)], text=True)
        defined, undefined = set(), set()
        for line in sym.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[1].upper() != "U":
                defined.add(parts[2])
            elif len(parts) >= 2 and parts[-2].upper() == "U":
                undefined.add(parts[-1])
        roots = ("Z_Init", "P_SetupLevel", "G_Ticker")
        report["required_roots"] = {root: root in defined for root in roots}
        report["undefined"] = sorted(undefined)
        report["undefined_count"] = len(undefined)
        report["reloc_bytes"] = reloc.stat().st_size
        libgcc = subprocess.check_output(
            [gcc, "-m68000", "-print-libgcc-file-name"], text=True).strip()
        elf = out / "logic-roots.elf"
        cmd = [gcc, "-m68000", "-nostdlib", "-Wl,--gc-sections",
               "-Wl,--unresolved-symbols=ignore-all", "-Wl,-Ttext=0",
               "-Wl,-e,G_Ticker", "-Wl,-Map," + str(out / "logic.map")]
        cmd += ["-Wl,-u," + root for root in roots]
        p = subprocess.run(cmd + ["-o", str(elf), str(reloc), libgcc],
                           capture_output=True, text=True)
        report["gc_link_ok"] = not p.returncode
        report["gc_link_error"] = p.stderr[-1500:]
        if not p.returncode:
            sections = subprocess.check_output([size, "-A", str(elf)], text=True)
            report["sections"] = sections
            (out / "sections.txt").write_text(sections)
(out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
print("S1d LOGIC SLICE: COMPILED %d/%d" % (len(objects), len(names)))
print("Reloc link:", report.get("reloc_link_ok"))
print("GC link:", report.get("gc_link_ok"))
print("Undefined:", report.get("undefined_count", "n/a"))
print("Required roots:", report.get("required_roots", {}))
for failure in failures:
    print("COMPILE FAIL:", failure["source"])
    print(failure["error"])
print("Report:", out / "report.json")
if failures or not report.get("reloc_link_ok") or not report.get("gc_link_ok"):
    raise SystemExit("S1d dependency preflight FAIL; see private report")
