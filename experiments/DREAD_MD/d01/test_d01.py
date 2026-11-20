"""DREAD-MD D01 in BlastEm: run the built-in bench route, report FPS and render stats,
save a few frames (rebuilt from the RAM framebuffer) as PNG. Numbers + shareware images only."""
import json, os, struct, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts/lab"))
from r64a_rsp_capture import RSP

rom, elf, outdir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
outdir.mkdir(parents=True, exist_ok=True)
nm = os.environ.get("NM", str(Path.home() / "mars/m68k-elf/bin/m68k-elf-nm"))
sym, size = {}, {}
for line in subprocess.check_output([nm, "-S", elf], text=True).splitlines():
    f = line.split()
    if len(f) == 4: sym[f[3]] = int(f[0], 16) & 0xffffff; size[f[3]] = int(f[1], 16)
    elif len(f) == 3: sym.setdefault(f[2], int(f[0], 16) & 0xffffff)
COLB = int(os.environ.get("COLB", "1"))
VW, VH = (80, 144) if COLB == 2 else (160, 72)
TC = VW * COLB // 4
FB = TC * VH * 4
def rd(g, name, n):
    return int.from_bytes(g.readmem(sym[name], n), "big")
def readbig(g, addr, n):
    out = bytearray()
    while len(out) < n:
        k = min(192, n - len(out)); out += g.readmem(addr + len(out), k)
    return bytes(out)
pal = readbig_cache = None
g = RSP(os.environ["BLASTEM"], rom, 9000, 900)
res = {}
shots = []
try:
    g.req("qSupported")
    # BSS is cleared by the startup code: request the bench once main() runs
    assert g.req(f"Z0,{sym['main']:x},2") == "OK"
    g.cont()
    assert g.req(f"z0,{sym['main']:x},2") == "OK"
    assert g.req("M%x,2:0001" % sym["bench_req"]) == "OK"
    if os.environ.get("DBG"): assert g.req("M%x,2:%04x" % (sym["dbg_flags"], int(os.environ["DBG"]))) == "OK"
    assert g.req(f"Z0,{sym['R_RenderView']:x},2") == "OK"
    npal = rd(g, "num_palettes", 2) if "num_palettes" in sym else 1
    DAC = [0, 52, 87, 116, 144, 172, 206, 255]
    pals = []
    for k in range(npal):
        pl = struct.unpack(">16H", readbig(g, sym["md_palette"] + 32 * k, 32))
        pals.append([(DAC[c >> 1 & 7], DAC[c >> 5 & 7], DAC[c >> 9 & 7]) for c in pl])
    import bisect, collections
    vec = int.from_bytes(rom.read_bytes()[0x78:0x7C], "big") & 0xffffff
    assert g.req(f"Z0,{vec:x},2") == "OK"
    funcs = sorted((a, n) for n, a in sym.items() if a < 0x400000)
    keys = [f[0] for f in funcs]
    hist = collections.Counter(); fine = collections.Counter()
    frames = 0; stats = []; cv = []; since = 0
    want = {1, 20, 45, 70, 95, 120, 150}
    while True:
        g.cont()
        regs = g.req("g")
        pc = int(regs[17 * 8:18 * 8], 16) & 0xffffff
        if pc == vec:   # VBlank: the stacked PC is a 60 Hz profile sample
            sp = int(regs[15 * 8:16 * 8], 16) & 0xffffff
            ipc = int.from_bytes(g.readmem(sp + 2, 4), "big") & 0xffffff
            k = bisect.bisect_right(keys, ipc) - 1
            hist[funcs[k][1] if k >= 0 else hex(ipc)] += 1
            since += 1
            if since > 600:   # no frame for 10 s: stuck or crashed
                res["stuck_pc"] = [hex(ipc), funcs[k][1] if k >= 0 else "?", hex(ipc - funcs[k][0]) if k >= 0 else ""]
                res["stuck_regs"] = regs[:16 * 8]
                break
            if k >= 0 and funcs[k][1] in ("draw_seg", "seg_columns", "render_node"): fine[ipc] += 1
            continue
        frames += 1; since = 0
        done = rd(g, "bench_done", 2)
        segs, nodes = rd(g, "frame_segs", 2), rd(g, "frame_nodes", 2)
        if frames > 1: stats.append((segs, nodes)); cv.append((rd(g, "frame_cols", 2), rd(g, "frame_anchors", 2)))
        if frames in want:
            cb = rd(g, "cur_buf", 2)
            fb = readbig(g, sym["fbuf"] + ((cb ^ 1) * FB if COLB == 1 else 0), FB)
            nt = struct.unpack(">%dH" % (VH // 8 * 32), readbig(g, sym["ntbuf"], VH // 8 * 64)) if "ntbuf" in sym else None
            from PIL import Image
            RD = 2 if COLB == 1 else 1
            im = Image.new("RGB", (TC * 8, VH * RD))
            px = im.load()
            for y in range(VH * RD):
                r = y // RD
                for x in range(TC * 8):
                    bx = x >> 1
                    b = fb[(bx >> 2) * VH * 4 + r * 4 + (bx & 3)]
                    rgb = pals[0]
                    px[x, y] = rgb[b & 15] if (x & 1) else rgb[b >> 4]
            im.resize((TC * 16, VH * RD * 2), Image.NEAREST).save(outdir / f"frame_{frames:03d}.png")
            shots.append(frames)
        if done:
            res = {"bench_frames": rd(g, "bench_frames", 4), "bench_vints": rd(g, "bench_vints", 4)}
            res["fps"] = round(res["bench_frames"] * 60 / max(res["bench_vints"], 1), 2)
            ts, tl, tt, ta, tf, tx = (rd(g, n, 4) if n in sym else 0 for n in ("tm_setup", "tm_loop", "tm_total", "tm_anchor", "tm_fill", "tm_tex"))
            fr = max(frames, 1); ms = 1000 / 60 / 262
            res["ms_per_frame"] = {"render_total": round(tt * ms / fr, 1), "seg_setup": round(ts * ms / fr, 1), "column_loops": round(tl * ms / fr, 1), "anchors": round(ta * ms / fr, 1), "fills": round(tf * ms / fr, 1), "tex": round(tx * ms / fr, 1),
                                   "frame": round(res["bench_vints"] * 1000 / 60 / max(res["bench_frames"], 1), 1)}
            break
        if frames > 1500: res["timeout"] = True; break
    if stats:
        s = [a for a, b in stats]; n = [b for a, b in stats]
        res.update(segs_avg=round(sum(s) / len(s), 1), segs_max=max(s), nodes_avg=round(sum(n) / len(n), 1), nodes_max=max(n))
    res["shots"] = shots
    if cv: res.update(col_visits_avg=round(sum(a for a, b in cv) / len(cv), 1), anchors_avg=round(sum(b for a, b in cv) / len(cv), 1))
    tot = sum(hist.values())
    a2l = os.environ.get("ADDR2LINE")
    lines = collections.Counter()
    if a2l and fine:
        addrs = list(fine)
        out = subprocess.check_output([a2l, "-e", str(elf)] + [hex(a) for a in addrs], text=True).splitlines()
        for a, l in zip(addrs, out): lines[l.split("/")[-1]] += fine[a]
    tot2 = max(sum(hist.values()), 1)
    res["hot_lines"] = [(l, round(100 * c / tot2, 1)) for l, c in lines.most_common(25)]
    res["profile"] = [(n, round(100 * c / tot, 1)) for n, c in hist.most_common(25)]
finally:
    g.close()
print("D01 RESULT", json.dumps(res), flush=True)
(outdir / "result.json").write_text(json.dumps(res, indent=1))
