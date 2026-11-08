"""Run the N0 cell-image ROM in BlastEm (Sega CD) and read the verdict from symbols."""
import os, subprocess, sys
from pathlib import Path
from r64a_rsp_capture import RSP

rom, elf = map(Path, sys.argv[1:])
nm = Path.home() / "mars/m68k-elf/bin/m68k-elf-nm"
sym = {}
for line in subprocess.check_output([nm, elf], text=True).splitlines():
    f = line.split()
    if len(f) == 3: sym[f[2]] = int(f[0], 16) & 0xffffff
g = RSP(os.environ["BLASTEM"], rom, 3000, 120)
try:
    g.req("qSupported")
    stop = sym["cell_complete"]
    assert g.req(f"Z0,{stop:x},2") == "OK"
    g.cont()
    state = int.from_bytes(g.readmem(sym["cell_state"], 2), "big")
    raw = g.readmem(sym["cell_result"], 48)
    rows = [[int.from_bytes(raw[i * 16 + j * 4:i * 16 + j * 4 + 4], "big") for j in range(4)] for i in range(3)]
    for label, (n, bad, ticks, late) in zip(("cpu-cell-view", "dma16k-display-off", "dma-3vbl-display-on"), rows):
        print(label, dict(runs=n, bad_words=bad, ticks=ticks, late=late, ms_per_run="%.3f" % (ticks * 0.03072 / max(n, 1))))
    ok = state == 4 and all(r[1] == 0 for r in rows)
    print("state", state, "blastem:", "PASS" if ok else "FAIL")
    assert ok
finally:
    g.close()
