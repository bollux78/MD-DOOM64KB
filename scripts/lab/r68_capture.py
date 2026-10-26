#!/usr/bin/env python3
"""R68 capture + analysis (BlastEm GDB RSP, read-only, no GDB binary needed).

Breaks at R68_FrameMark() once per game frame, reads the r68_block_t the ROM keeps in the
SGDK heap and records, for every frame: vblank stamps (logic / render split), workload
counters and the HInt PC samples. Then writes frames.jsonl, summary.json and report.md:
frame-time distribution, share of time in the slowest frames, cycle cost per workload unit
(least squares), and the PC profile overall and for slow vs fast frames.

NOT a benchmark: the ROM carries sampler overhead (a few percent). It answers WHERE the time
goes, never how fast the game is. The 10_000 emulated-frame cap was lifted by the maintainer (2026-10-26) so whole-demo captures are possible; the capture stops when the demo ends;
DEMO3 at ~8 vblanks per game frame reaches about tic 1000 inside that limit.
"""
import re, argparse, bisect, collections, importlib.util, json, os, pathlib, shutil, struct, subprocess, sys

RING = 128
NMARKS = 8
FMT = ">%dHHHIIIHHIIIIii12H%dI" % (RING, NMARKS)
SIZE = struct.calcsize(FMT)
assert SIZE == 356, SIZE
COUNTERS = ["bspnode", "bbox", "addline", "seg", "col", "wall", "flat", "pta",
            "sprproj", "sprdraw", "sight", "spare"]
MAGIC = 0x52363850
LINES = 262
LINE_CYCLES = 7670453 / 60.0 / LINES
PHASES = ["logic", "setup", "bsp+planes", "masked+sprites", "hud+menu", "flip+video"]


GROUPS = [  # (group, regex on symbol name); first match wins
    ("wall kernel (ASM)", r"^R60_WallColumn"),
    ("wall column C glue", r"^(R_RenderSegLoop|R42_DrawPackedWall|R_DrawSegTextureColumn|R_GetColumn)"),
    ("flat span/column", r"^(R_DrawColumnFlat|R_DrawSpan|R_MapPlane|R_MakeSpans|R_DoDrawPlane|R_DrawPlanes|R_FreeSkyPatch)"),
    ("sprite/masked draw", r"^(R_DrawColumnSprite|R_DrawMaskedColumn|R_DrawVisSprite|R_DrawMasked|R_DrawPlayerSprites)"),
    ("segment setup + geometry", r"^(R_StoreWallRange|R_PointToAngle|R_ScaleFromGlobalAngle|__mulsi3|__udivsi3|__divsi3|__umodsi3|FixedReciprocal|FixedDiv|FixedMul|R_PointToDist)"),
    ("BSP traversal", r"^(R_AddLine|R_CheckBBox|R_RenderBSPNode|R_RenderBspSubsector|R_ClipWallSegment|R_Subsector|R_CheckOpenings|R_PointOnSide)"),
    ("sprite project/sort", r"^(R_ProjectSprite|R_AddSprites)"),
    ("game logic", r"^(P_|G_|A_|T_|M_Random|D_Think|S_)"),
    ("map streaming", r"^(R23_|R27_|node_read|R2\d_)"),
]


def group_of(name):
    for g, rx in GROUPS:
        if re.search(rx, name):
            return g
    return "other"


def group_table(frames, code, label):
    h = collections.Counter(); tot = 0
    for f in frames:
        for b in f["ring"]:
            h[group_of(symbolize(code, b * 8))] += 1; tot += 1
    if not tot:
        return []
    rows = ["", "## Function groups: %s (%d samples)" % (label, tot), "", "| group | samples | share |", "|---|---:|---:|"]
    for g, c in h.most_common():
        rows.append("| %s | %d | %.1f%% |" % (g, c, 100.0 * c / tot))
    return rows


def mark_lines(m):
    """(vblank << 8 | V counter) -> absolute NTSC lines since the vblank interrupt (vint at line 224)."""
    vb, v = m >> 8, m & 0xFF
    # V counter 0..0xEA then 0xE5..0xFF: values 0xE5..0xEA are ambiguous (lines 229-234 vs 235-240, both
    # inside vblank); they are decoded as the first pass. Rare: only stamps taken in vblank are affected.
    line = v if v <= 0xEA else 235 + (v - 0xE5)
    return vb * LINES + (line - 224) % LINES


def phase_lines(marks):
    """Lines spent in each phase: 0->1 logic, 1->2 setup, 2->3 bsp+planes, 3->4 masked, 4->5 hud, 5->6 flip."""
    if not all(marks[:7]):
        return None
    t = [mark_lines(m) for m in marks[:7]]
    d = [t[i + 1] - t[i] for i in range(6)]
    return d if all(x >= 0 for x in d) else None


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
    c = dict(zip(COUNTERS, v[RING + 13:RING + 25]))
    marks = [m for m in v[RING + 25:RING + 25 + NMARKS]]
    if magic != MAGIC:
        raise ValueError("bad R68 magic %08x" % magic)
    head = min(head, RING)
    return dict(frame=frame, vb_start=vb0, vb_logic=vb1, vb_end=vb2, tic_start=t0, tic_end=t1,
                samples=samples, head=head, bad=bad, c=c, marks=marks, ring=ring[:head], version=version, ring_n=ring_n)


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
    ph = [phase_lines(f["marks"]) for f in frames if "marks" in f]
    ph = [p for p in ph if p]
    if ph:
        sums = [sum(p[i] for p in ph) for i in range(6)]
        tt = sum(sums) or 1
        res["phases"] = {"frames": len(ph), "lines_mean": [x / len(ph) for x in sums],
                         "cycles_mean": [x * LINE_CYCLES / len(ph) for x in sums],
                         "share": [x / tt for x in sums]}
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
    def rows(h, t, top=40):
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
    if res.get("phases"):
        P = res["phases"]
        L += ["", "## Phase breakdown (%d frames, V-counter resolution ~%d cycles)" % (P["frames"], LINE_CYCLES), "",
              "| phase | mean lines | mean cycles | share |", "|---|---:|---:|---:|"]
        for i, nme in enumerate(PHASES):
            L.append("| %s | %.1f | %.0f | %.1f%% |" % (nme, P["lines_mean"][i], P["cycles_mean"][i], 100 * P["share"][i]))
    thirds = [frames[i * n // 3:(i + 1) * n // 3] for i in range(3)] if n >= 30 else []
    L += group_table(frames, code, "all frames")
    for i, part in enumerate(thirds):
        L += group_table(part, code, "demo third %d (tics %d..%d, mean %.1f vb/frame)" % (
            i + 1, part[0]["tic_start"], part[-1]["tic_end"],
            sum(f["vb_end"] - f["vb_start"] for f in part) / len(part)))
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


def objdump_exe():
    od = os.environ.get("M68K_OBJDUMP")
    if od and pathlib.Path(od).is_file():
        return od
    p = pathlib.Path.home() / "mars/m68k-elf/bin/m68k-elf-objdump"
    return str(p) if p.is_file() else shutil.which("m68k-elf-objdump")


def parse_listing(txt):
    """objdump -d (no raw bytes) -> [(address, 'mnemonic operands')] in address order."""
    out = []
    for l in txt.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\t(.*)$", l)
        if m and m.group(2).strip():
            out.append((int(m.group(1), 16), " ".join(m.group(2).split())))
    return out


def bucket_text(insns, a, width=8):
    """Instructions that overlap the sampled 8-byte bucket [a, a+width): the one containing a plus those starting inside."""
    starts = [x for x, _ in insns]
    i = max(bisect.bisect_right(starts, a) - 1, 0)
    sel = [t for x, t in insns[i:] if x < a + width]
    return " ; ".join(sel) if sel else "(outside listing)"


def hotspots(frames, code, elf, outdir, top_funcs=8, top_buckets=10):
    """Instruction-level view: for the busiest functions, the busiest 8-byte buckets with disassembly."""
    starts = [a for a, _ in code]
    hist = collections.Counter()
    for f in frames:
        for b in f["ring"]:
            hist[b * 8] += 1
    total = sum(hist.values()) or 1
    per_func = collections.Counter()
    for a, c in hist.items():
        i = bisect.bisect_right(starts, a) - 1
        if i >= 0:
            per_func[(code[i][0], code[i][1])] += c
    od = objdump_exe()
    L = ["# R68 hot spots (8-byte buckets, all frames; total samples %d)" % total, ""]
    for (fa, fn), fc in per_func.most_common(top_funcs):
        i = bisect.bisect_right(starts, fa)
        fend = code[i][0] if i < len(code) else fa + 4096
        L.append("## %s  [%#x..%#x)  %d samples (%.1f%%)" % (fn, fa, fend, fc, 100.0 * fc / total))
        bk = sorted(((a, c) for a, c in hist.items() if fa <= a < fend), key=lambda x: -x[1])[:top_buckets]
        # Disassemble the WHOLE function from its first byte: starting objdump in the middle of an instruction
        # (as the first version did) yields garbage ('.short', 'Address out of bounds').
        insns = []
        if od:
            try:
                txt = subprocess.run([od, "-d", "--no-show-raw-insn", "--start-address=%d" % fa, "--stop-address=%d" % fend,
                                      str(elf)], check=True, capture_output=True, text=True).stdout
                insns = parse_listing(txt)
            except Exception:
                insns = None
        for a, c in bk:
            ins = "(no objdump)" if not od else ("(objdump failed)" if insns is None else bucket_text(insns, a))
            L.append("- %06x  %4d (%.1f%% of func)  %s" % (a, c, 100.0 * c / fc, ins))
        L.append("")
    (pathlib.Path(outdir) / "hot.md").write_text("\n".join(L) + "\n")


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
    max_tic, stalled = 0, 0
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
                # whole-demo captures: stop when the demo ends (tic restarts, or stops advancing for 300 frames)
                if f["tic_end"] + 5 < max_tic:
                    print("demo restarted at frame", f["frame"], flush=True); break
                if f["tic_end"] > max_tic:
                    max_tic, stalled = f["tic_end"], 0
                else:
                    stalled += 1
                    if stalled >= 300:
                        print("demo finished (tic stopped advancing)", flush=True); break
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
    res = analyze(frames, code, out)
    try:
        hotspots(frames, code, args.elf, out)
    except Exception as e:  # diagnostic extra, never fail the capture
        print("hotspots skipped:", e, file=sys.stderr)
    return res


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
