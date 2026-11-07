#!/usr/bin/env python3
"""S1c genuine engine link probe, NOT a runnable Sega CD engine.
Usage: engine_probe.py S0_OBJECT_DIR OUT_DIR

Link existing R128 68000 engine objects, force live Z_Init/P_SetupLevel/G_Ticker
sections, inspect unresolved platform symbols and memory budget. This probe
does not assert that the Sega CD executes the engine.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

s0, out = [Path(v).resolve() for v in sys.argv[1:]]
out.mkdir(parents=True, exist_ok=True)
tool = Path(os.environ.get("M68K_BIN", str(Path.home() / "mars/m68k-elf/bin")))
gcc, nm, size = (str(tool / ("m68k-elf-" + x)) for x in ("gcc", "nm", "size"))
engine = s0 / "engine-r.o"
if not engine.is_file():
    raise SystemExit("S1c BLOCKED: S0 engine-r.o not found")
roots = ["Z_Init", "P_SetupLevel", "G_Ticker"]
defined = subprocess.check_output([nm, "--defined-only", str(engine)], text=True)
symbols = {line.split()[-1] for line in defined.splitlines() if line.split()}
missing = [root for root in roots if root not in symbols]
if missing:
    raise SystemExit("S1c BLOCKED: essential symbols absent: " + ", ".join(missing))
libgcc = subprocess.check_output([gcc, "-m68000", "-print-libgcc-file-name"], text=True).strip()
elf = out / "s1c-roots.elf"
link = [gcc, "-m68000", "-nostdlib", "-Wl,--gc-sections",
        "-Wl,--unresolved-symbols=ignore-all", "-Wl,-e,G_Ticker",
        "-Wl,-Ttext=0x6000", "-Wl,-Map," + str(out / "s1c-roots.map")]
link += ["-Wl,-u," + root for root in roots]
link += ["-o", str(elf), str(engine), libgcc]
p = subprocess.run(link, capture_output=True, text=True)
(out / "link.log").write_text(p.stdout + p.stderr)
if p.returncode:
    raise SystemExit("S1c link FAIL: " + p.stderr[-2500:])
sections = subprocess.check_output([size, "-A", str(elf)], text=True)
(out / "sections.txt").write_text(sections)
unresolved = subprocess.check_output([nm, "-u", str(engine)], text=True)
names = sorted(set(line.split()[-1] for line in unresolved.splitlines() if line.split()))
def platform(name):
    return bool(re.match(r"^(VDP_|SYS_|DMA_|Z80_|XGM|JOY_|PAL_|SPR_|TIM_|MEM_|SND_|BMP_|KLog|I_|R_|G_|W_)", name))
summary = {
    "label": "S1c dependency/link probe only — not executable",
    "roots": roots,
    "object_bytes": engine.stat().st_size,
    "linked_elf_bytes": elf.stat().st_size,
    "unresolved_relocatable": names,
    "platform_like_unresolved": [x for x in names if platform(x)],
    "sections_report": sections,
    "result": "PASS: engine roots linked for dependency inspection, NOT gameplay"
}
(out / "report.json").write_text(json.dumps(summary, indent=2) + "\n")
print("S1c ENGINE LINK PROBE PASS; NOT A RUNNABLE S1")
print("Required roots:", ", ".join(roots))
print("Relocatable undefined:", len(names))
print("Platform-like:", " ".join(summary["platform_like_unresolved"]))
print(sections)
print("Artifacts:", out)
