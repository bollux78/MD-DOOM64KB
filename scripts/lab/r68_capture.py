#!/usr/bin/env python3
"""R68 capture + analysis (BlastEm GDB RSP, read-only, no GDB binary needed).

Breaks at R68_FrameMark() once per game frame, reads the r68_block_t the ROM keeps in the
SGDK heap and records, for every frame: vblank stamps (logic / render split), workload
counters and the HInt PC samples. Then writes frames.jsonl, summary.json and report.md:
frame-time distribution, share of time in the slowest frames, cycle cost per workload unit
(least squares), and the PC profile overall and for slow vs fast frames.

NOT a benchmark: the ROM carries sampler overhead (a few percent). It answers WHERE the time
goes, never how fast the game is. Max 10_000 emulated frames per BlastEm process by default;
DEMO3 at ~8 vblanks per game frame reaches about tic 1000 inside that limit.
"""
import argparse, bisect, collections, importlib.util, json, os, pathlib, shutil, struct, subprocess, sys

RING = 128
FMT = ">%dHHHIIIHHIIIIii12H" % RING
SIZE = struct.calcsize(FMT)
assert SIZE == 324, SIZE
COUNTERS = ["bspnode", "bbox", "addline", "seg", "col", "wall", "flat", "pta",
            "sprproj", "sprdraw", "sight", "spare"]
MAGIC = 0x52363850
VB_CYCLES = 7670453 / 60.0        # 68000 cycles per NTSC vblank at the stock clock


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_block(raw):
    if len(raw) != SIZE:
        raise ValueError("block size %d != %d" % (len(raw), SIZE))
    v = struct.unpack(FMT, raw)
    ring = list(v[:RING])
    (head, _pad, samples, bad, magic, version, ring_n, frame, vb0, vb1, vb2, t0, t1) = v[RING:RING + 13]
    c = dict(zip(COUNTERS, v[RING + 13:]))
    if magic != MAGIC:
        raise ValueError("bad R68 magic %08x" % magic)
    head = min(head, RING)
    return dict(frame=frame, vb_start=vb0, vb_logic=vb1, vb_end=vb2, tic_start=t0, tic_end=t1,
                samples=samples, head=head, bad=bad, c=c, ring=ring[:head], version=version, ring_n=ring_n)


def read_symbols(elf):
    """name -> address for exact lookups, plus a sorted code-symbol table for the PC profile."""
    nm = os.environ.get("M68K_NM") or str(pathlib.Path.home() / "mars/m68k-elf/bin/m68k-elf-nm")
    if not pathlib.Path(nm).is_file():
        nm = shutil.which("m68k-elf-nm") or nm
    out = subprocess.run([nm, "-n", "--defined-only", str(elf)], check=True, capture_output=True, text=True).stdout
    names, code = {}, []
    for line in out.splitlines():
        p = line.split()
        if len(p) < 3:
            continue
        try:
            a = int(p[0], 16)
        except ValueError:
            continue
        names[p[2]] = a
        if p[1] in "tTwW":
            code.append((a, p[2]))
    code.sort()
    return names, code


def symbolize(code, pc):
    i = bisect.bisect_right([a for a, _ in code], pc) - 1
    return code[i][1] if i >= 0 else "?"


def pct(sorted_vals, q):
    if not sorted_vals:
        return 0
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))]


def analyze(frames, code, outdir):
    n = len(frames)
    tot = [f["vb_end"] - f["vb_start"] for f in frames]
    logic = [f["vb_logic"] - f["vb_start"] for f in frames]
    rend = [f["vb_end"] - f["vb_logic"] for f in frames]
    total_vb = sum(tot) or 1
    srt = sorted(tot)
    res = {"frames": n, "total_vblanks": sum(tot), "mean_vb": sum(tot) / max(n, 1),
           "p50": pct(srt, .5), "p90": pct(srt, .9), "p99": pct(srt, .99), "max": srt[-1] if srt else 0,
           "logic_share": sum(logic) / total_vb, "render_share": sum(rend) / total_vb}
    order = sorted(range(n), key=lambda i: -tot[i])
    for q in (0.1, 0.2, 0.3, 0.5):
        k = max(1, int(round(q * n)))
        res["time_share_slowest_%d%%" % int(q * 100)] = sum(tot[i] for i in order[:k]) / total_vb
    bins = [(1, 4), (5, 8), (9, 12), (13, 16), (17, 24), (25, 10 ** 9)]
    res["bins"] = [{"vb": "%d-%s" % (lo, hi if hi < 10 ** 9 else "+"),
                    "frames": sum(1 for t in tot if lo <= t <= hi),
                    "time_share": sum(t for t in tot if lo <= t <= hi) / total_vb} for lo, hi in bins]
    res["mean_counters"] = {k: sum(f["c"][k] for f in frames) / max(n, 1) for k in COUNTERS if k != "spare"}
    # cycles per workload unit by least squares: vb_total*VB_CYCLES ~ intercept + sum(coef*counter)
    try:
        import numpy as np
        keys = [k for k in COUNTERS if k != "spare" and any(f["c"][k] for f in frames)]
        A = np.array([[1.0] + [float(f["c"][k]) for k in keys] for f in frames])
        y = np.array(tot, dtype=float) * VB_CYCLES
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ coef
        ss_res = float(((y - pred) ** 2).sum()); ss_tot = float(((y - y.mean()) ** 2).sum()) or 1.0
        res["fit"] = {"r2": 1 - ss_res / ss_tot, "intercept_cycles": float(coef[0]),
                      "cycles_per_unit": {k: float(c) for k, c in zip(keys, coef[1:])}}
        res["corr"] = {k: float(np.corrcoef(A[:, 1 + i], y)[0, 1]) if A[:, 1 + i].std() else 0.0
                       for i, k in enumerate(keys)}
    except ImportError:
        res["fit"] = None
    # PC profile
    def profile(idx):
        h = collections.Counter()
        total = 0
        for i in idx:
            for b in frames[i]["ring"]:
                h[symbolize(code, b * 8)] += 1
                total += 1
        return h, total
    allh, alltot = profile(range(n))
    k20 = max(1, int(round(0.2 * n)))
    slow = order[:k20]
    fast = order[n // 2:]
    slowh, slowt = profile(slow)
    fasth, fastt = profile(fast)
    def rows(h, t, top=25):
        return [(name, c, c / t if t else 0) for name, c in h.most_common(top)]
    res["samples_total"] = alltot
    res["samples_lost"] = sum(max(0, f["samples"] - f["head"]) for f in frames)
    res["bad_frames"] = sum(f["bad"] for f in frames)
    res["profile_all"] = rows(allh, alltot)
    res["profile_slow20"] = rows(slowh, slowt)
    res["profile_fast50"] = rows(fasth, fastt)
    outdir = pathlib.Path(outdir)
    (outdir / "summary.json").write_text(json.dumps(res, indent=1))
    L = ["# R68 report", "",
         "Frames: %d, total %d vblanks, mean %.2f vb (%.2f FPS equivalent), p50 %d, p90 %d, p99 %d, max %d." % (
             n, res["total_vblanks"], res["mean_vb"], 60.0 / res["mean_vb"] if res["mean_vb"] else 0,
             res["p50"], res["p90"], res["p99"], res["max"]),
         "Logic (TryRunTics) %.1f%% / render+video (D_Display) %.1f%% of vblanks." % (
             100 * res["logic_share"], 100 * res["render_share"]), "",
         "## Share of total time in the slowest frames", ""]
    for q in (10, 20, 30, 50):
        L.append("- slowest %d%% of frames: %.1f%% of the time" % (q, 100 * res["time_share_slowest_%d%%" % q]))
    L += ["", "## Frame cost histogram", "", "| vblanks | frames | share of time |", "|---|---:|---:|"]
    for b in res["bins"]:
        L.append("| %s | %d | %.1f%% |" % (b["vb"], b["frames"], 100 * b["time_share"]))
    L += ["", "## Mean workload per frame", ""]
    L += ["- %s: %.1f" % (k, v) for k, v in res["mean_counters"].items()]
    if res["fit"]:
        f = res["fit"]
        L += ["", "## Cost model (least squares, 68000 cycles per unit)", "",
              "R^2 = %.3f; fixed cost per frame = %.0f cycles" % (f["r2"], f["intercept_cycles"]), ""]
        for k, c in sorted(f["cycles_per_unit"].items(), key=lambda kv: -abs(kv[1])):
            L.append("- %s: %.0f cycles/unit (corr %.2f)" % (k, c, res["corr"][k]))
        L.append("")
        L.append("Counters are correlated with each other; read the coefficients as a guide, not as exact costs.")
    for title, key in (("All frames", "profile_all"), ("Slowest 20% of frames", "profile_slow20"),
                       ("Fastest 50% of frames", "profile_fast50")):
        L += ["", "## PC profile: " + title, "", "| function | samples | share |", "|---|---:|---:|"]
        L += ["| %s | %d | %.1f%% |" % (r[0], r[1], 100 * r[2]) for r in res[key]]
    L += ["", "Samples come from the horizontal interrupt, so VBlank lines are not sampled. "
          "Lost samples (ring full): %d. Frames with unexpected HInt stack layout: %d." % (
              res["samples_lost"], res["bad_frames"])]
    (outdir / "report.md").write_text("\n".join(L) + "\n")
    return res


def capture(args):
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    names, code = read_symbols(args.elf)
    for need in ("r68_ptr", "R68_FrameMark", "_g_gametic"):
        if need not in names:
            raise RuntimeError("ELF missing symbol %s (is this an R68 ROM?)" % need)
    if code and code[-1][0] > 0x7FFFF * 1 and any(a > 0x7FFFF for a, _ in code):
        print("WARNING: code above 512 KiB; PC>>3 samples saturate there", file=sys.stderr)
    rsp = load_rsp()
    g = rsp.RSP(args.blastem, args.rom, args.max_emulated_frames, args.timeout)
    frames, seen = [], set()
    try:
        g.req("qSupported")
        assert g.req("Z0,%x,2" % names["R68_FrameMark"]) == "OK"
        ptr = None
        with open(out / "frames.jsonl", "w") as jf:
            for _ in range(args.max_breaks):
                try:
                    g.cont()
                except RuntimeError as e:
                    if "exited" in str(e) or "EOF" in str(e):
                        print("BlastEm ended:", e, flush=True); break
                    raise
                if ptr is None:
                    ptr = int.from_bytes(g.readmem(names["r68_ptr"], 4), "big") & 0xFFFFFF
                    if not ptr:
                        continue
                f = parse_block(g.readmem(ptr, SIZE))
                if f["frame"] in seen:
                    continue
                seen.add(f["frame"])
                if f["tic_end"] < args.start_tic:
                    continue
                frames.append(f)
                jf.write(json.dumps({k: v for k, v in f.items() if k != "ring"} | {"ring_n_used": len(f["ring"])}) + "\n")
                if len(frames) >= args.max_frames:
                    break
    finally:
        g.close()
    (out / "rings.json").write_text(json.dumps([f["ring"] for f in frames]))
    if not frames:
        raise RuntimeError("no frames captured")
    return analyze(frames, code, out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True)
    ap.add_argument("--elf", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--max-frames", type=int, default=100000, help="game frames to record")
    ap.add_argument("--max-emulated-frames", type=int, default=10000)
    ap.add_argument("--max-breaks", type=int, default=200000)
    ap.add_argument("--start-tic", type=int, default=1)
    ap.add_argument("--timeout", type=float, default=120.0)
    a = ap.parse_args()
    r = capture(a)
    print("frames", r["frames"], "mean vb %.2f" % r["mean_vb"], "slowest20%% share %.1f%%" % (100 * r["time_share_slowest_20%"]))


if __name__ == "__main__":
    main()
