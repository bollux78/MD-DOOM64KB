"""Run the S1a ROM in BlastEm (Sega CD, Mode 1) and read its verdict from the ELF symbols."""
import os, subprocess, sys
from pathlib import Path
from r64a_rsp_capture import RSP

rom, elf = map(Path, sys.argv[1:])
nm = Path.home() / "mars/m68k-elf/bin/m68k-elf-nm"
sym = {}
for line in subprocess.check_output([nm, elf], text=True).splitlines():
    f = line.split()
    if len(f) == 3: sym[f[2].split(".")[0]] = int(f[0], 16) & 0xffffff
g = RSP(os.environ["BLASTEM"], rom, 9000, 600)
try:
    g.req("qSupported")
    stop = sym["s1a_complete"]
    for name in ("S1A_Test", "s1a_mark", "s1a_complete"):
        assert g.req(f"Z0,{sym[name]:x},2") == "OK", name
    while True:
        g.cont()
        pc = int(g.req("g")[17 * 8:18 * 8], 16) & 0xffffff
        if pc == stop:
            break
        stage = int.from_bytes(g.readmem(sym["s1a_stage"], 2), "big")
        print("reached", "S1A_Test" if pc == sym["S1A_Test"] else "mark stage(before update) 0x%x" % stage, flush=True)
    rd = lambda n, k: int.from_bytes(g.readmem(sym[n], k), "big")
    state = rd("s1a_state", 2)
    md = [int.from_bytes(g.readmem(sym["s1a_md"] + 4 * i, 4), "big") for i in range(3)]
    sub = [int.from_bytes(g.readmem(sym["s1a_sub"] + 4 * i, 4), "big") for i in range(3)]
    r = dict(state=state, tests_bad=rd("s1a_tests_bad", 2), lumps=rd("s1a_lumps", 2), bytes=rd("s1a_bytes", 4),
             lump_bad=rd("s1a_lump_bad", 2), cache_md=hex(rd("s1a_cache_md", 4)), cache_sub=hex(rd("s1a_cache_sub", 4)),
             md=[hex(x) for x in md], sub=[hex(x) for x in sub])
    print("S1a:", r)
    ok = state == 4 and r["tests_bad"] == 0 and r["lump_bad"] == 0 and r["lumps"] > 5 and r["cache_md"] == r["cache_sub"]
    print("blastem:", "PASS" if ok else "FAIL")
    assert ok
finally:
    g.close()
