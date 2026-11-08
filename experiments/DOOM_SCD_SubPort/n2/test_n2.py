"""N2 in BlastEm (Sega CD): sub renders the E1M1 spawn; read the MD report and the frame's colour
histogram (numbers only, no image leaves the runner); then the ROM must continue into the game."""
import os, struct, subprocess, sys
from collections import Counter
from pathlib import Path
from r64a_rsp_capture import RSP

rom, elf = map(Path, sys.argv[1:])
nm = Path.home() / "mars/m68k-elf/bin/m68k-elf-nm"
sym = {}
for line in subprocess.check_output([nm, elf], text=True).splitlines():
    f = line.split()
    if len(f) == 3: sym[f[2].split(".")[0]] = int(f[0], 16) & 0xffffff
g = RSP(os.environ["BLASTEM"], rom, 9500, 900)
try:
    g.req("qSupported")
    for n in ("n2_frame_shown", "n2_complete", "I_Error"):
        assert g.req(f"Z0,{sym[n]:x},2") == "OK", n
    shown = 0
    while True:
        g.cont()
        pc = int(g.req("g")[17 * 8:18 * 8], 16) & 0xffffff
        if pc == sym["I_Error"]:
            print("MD I_Error reached"); break
        if pc == sym["n2_complete"]:
            break
        shown += 1
        if shown in (1, 24):
            # MD owns the bank the sub filled: linear 4bpp bitmap, lines 0..175, 152 bytes each.
            raw = g.readmem(0x600000, 176 * 256)
            hist = Counter()
            for y in range(0, 176, 4):
                for x in range(0, 152, 2):
                    hist[raw[y * 256 + x] & 15] += 1
            print("frame", shown, "colour histogram (sample index: count):", dict(sorted(hist.items())), flush=True)
    rep = struct.unpack(">4H6I", bytes(g.readmem(0x61F000, 32)))
    keys = ("stage", "frames", "errors", "timeouts", "bytes", "render_units", "expand_units", "columns", "pixels", "vblanks")
    r = dict(zip(keys, rep))
    if r["frames"]:
        r["render_ms_per_frame"] = round(r["render_units"] * 0.03072 / r["frames"], 2)
        r["expand_ms_per_frame"] = round(r["expand_units"] * 0.03072 / r["frames"], 2)
    print("N2 report:", r, flush=True)
    ok = r["stage"] == 5 and r["frames"] == 24 and not r["errors"] and not r["timeouts"]
    for n in ("n2_frame_shown", "n2_complete", "I_Error"):
        g.req(f"z0,{sym[n]:x},2")
    if ok:
        assert g.req(f"Z0,{sym['G_Ticker']:x},2") == "OK"
        g.cont()
        played = (int(g.req("g")[17 * 8:18 * 8], 16) & 0xffffff) == sym["G_Ticker"]
        print("game started after the result screen:", played)
        ok = played
    print("blastem:", "PASS" if ok else "FAIL")
    assert ok
finally:
    g.close()
