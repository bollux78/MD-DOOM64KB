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
    for name in ("S1A_Test", "s1a_mark", "s1a_complete", "I_Error"):
        assert g.req(f"Z0,{sym[name]:x},2") == "OK", name
    while True:
        g.cont()
        pc = int(g.req("g")[17 * 8:18 * 8], 16) & 0xffffff
        if pc == stop:
            break
        stage = int.from_bytes(g.readmem(0x61F000 + 44, 2), "big")
        if pc == sym["I_Error"]:
            print("reached I_Error (game error screen) after stage 0x%x" % stage, flush=True)
            break
        regs = g.req("g")
        sp = int(regs[15 * 8:16 * 8], 16) & 0xffffff
        arg = int.from_bytes(g.readmem(sp + 4, 4), "big") & 0xffff
        print("reached", "S1A_Test" if pc == sym["S1A_Test"] else "mark 0x%x" % arg, flush=True)
    import struct
    raw = bytes(g.readmem(0x61F000, 46))
    f = struct.unpack(">4H3I3I3IH", raw)
    state, tests_bad, lumps, lump_bad, nbytes, cmd, csub = f[:7]
    r = dict(state=state, tests_bad=tests_bad, lumps=lumps, bytes=nbytes, lump_bad=lump_bad,
             cache_md=hex(cmd), cache_sub=hex(csub), md=[hex(x) for x in f[7:10]], sub=[hex(x) for x in f[10:13]])
    print("S1a:", r)
    ok = state == 4 and r["tests_bad"] == 0 and r["lump_bad"] == 0 and r["lumps"] > 5 and r["cache_md"] == r["cache_sub"]
    print("blastem:", "PASS" if ok else "FAIL")
    assert ok
finally:
    g.close()
