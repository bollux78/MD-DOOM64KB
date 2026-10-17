#!/usr/bin/env python3
"""Fail-closed flags/symbol/RAM evidence, not a guarantee of identical code."""
import os, pathlib, shutil, subprocess, sys
p = pathlib.Path(sys.argv[1]); ids = sys.argv[2:]
if not ids: raise SystemExit("No builds to audit")
def flags(i):
    return sorted(x for x in (p/f"flags-{i}.txt").read_text().split()
                  if not x.startswith("-DDOOM_R20_") and x != "-DDOOM_R19_FLAT_DBRA"
                  and not x.startswith("doom-md-"))
base = flags(ids[0])
for i in ids[1:]:
    if flags(i) != base: raise SystemExit("non-experiment flags differ: " + i)
gdk = pathlib.Path(os.path.expanduser(os.environ.get("DOOM_MD_GDK", "~/mars/m68k-elf")))
nm = gdk/"bin/m68k-elf-nm"
if not nm.is_file():
    found = shutil.which("m68k-elf-nm")
    if not found: raise SystemExit("Missing m68k-elf-nm")
    nm = pathlib.Path(found)
lines = ["Check per-ROM noinline flags. Sizes alone do not prove code identity."]
lines.append(subprocess.check_output([str(nm),"--version"],text=True).splitlines()[0])
hot = ["R_Subsector", "R_DrawColumnSprite", "R_DrawColumnFlat", "R_RenderBSPNode",
       "P_CrossBSPNode", "P_CheckSight", "_bend", "__stack"]
for i in ids:
    elf = p/f"{i}.elf"
    if not elf.is_file() or not elf.stat().st_size: raise SystemExit("Missing ELF: " + i)
    text = subprocess.check_output([str(nm),"-S",str(elf)],text=True)
    if not text.strip(): raise SystemExit("Empty nm output: " + i)
    lines.append("\n"+i)
    matches = [l for l in text.splitlines() if any(l.split()[-1].split('.')[0] == h for h in hot)]
    if not any(l.split()[-1] == "_bend" for l in matches): raise SystemExit("Missing _bend: " + i)
    lines.extend(matches)
(p/"layout-report.txt").write_text("\n".join(lines)+"\n")
print("PASS: flags checked, all ELF/nm reads succeeded; symbols recorded")
