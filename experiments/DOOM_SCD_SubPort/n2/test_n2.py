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
    rep = struct.unpack(">4H9I", bytes(g.readmem(0x61F000, 44)))
    keys = ("stage", "frames", "errors", "timeouts", "bytes", "render_units", "expand_units", "columns", "pixels", "vblanks", "min_render", "column_units", "stack_depth")
    r = dict(zip(keys, rep))
    if r["frames"]:
        r["render_ms_per_frame"] = round(r["render_units"] * 0.03072 / r["frames"], 2)
        r["column_ms_per_frame"] = round(r["column_units"] * 0.03072 / r["frames"], 2)
        r["min_render_ms"] = round(r["min_render"] * 0.03072, 2)
        r["expand_ms_per_frame"] = round(r["expand_units"] * 0.03072 / r["frames"], 2)
    print("N2 report:", r, flush=True)
    if r["stage"] == 6:
        msg = bytes(g.readmem(0x61F100, 40)).split(b"\0")[0].decode("latin1")
        print("sub I_Error message:", repr(msg), flush=True)
    if r["stage"] == 5:
        bins = struct.unpack(">4096H", bytes(g.readmem(0x61C000, 8192)))
        sub_elf = elf.parent / "sub" / "n2-sub.elf"
        funcs = []
        for line in subprocess.check_output([nm, "-S", "--size-sort", str(sub_elf)], text=True).splitlines():
            f = line.split()
            if len(f) == 4 and f[2] in "Tt": funcs.append((int(f[0], 16), int(f[1], 16), f[3]))
        total = sum(bins) or 1
        per = Counter()
        for i, c in enumerate(bins):
            if not c: continue
            a = i * 64 + 32
            name = next((n for s0, sz, n in funcs if s0 <= a < s0 + sz), "0x%05x" % (i * 64))
            per[name] += c
        print("sub profile (%d samples during R_RenderPlayerView):" % total)
        for name, c in per.most_common(25):
            print("  %5.1f%%  %s" % (100.0 * c / total, name))
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
