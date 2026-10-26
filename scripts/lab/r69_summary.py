#!/usr/bin/env python3
"""R69: compare the instrumented PERF captures of several view windows on the SAME demo tics.
Usage: r69_summary.py DIST_DIR  (reads MANIFEST.json and capture-<name>/frames.jsonl)"""
import json, pathlib, sys

def window(view):
    mode, h, v = view
    h = min(32, h & ~7); v = min(32, v & ~7)
    xmin = (6 if mode else 2) + h // 4; xend = (70 if mode else 76) - h // 4
    return xend - xmin, (44 - v // 4) - (2 + v // 4)     # samples (each 4x4 px)

def main(d):
    d = pathlib.Path(d)
    rows = [r for r in json.loads((d / "MANIFEST.json").read_text()) if r.get("r68_prof")]
    data = {}
    for r in rows:
        name = r["rom"].replace("doom-md-r60-", "").replace(".bin", "")
        p = d / ("capture-" + name) / "frames.jsonl"
        if not p.is_file():
            print("missing", p); continue
        fr = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        data[name] = (r, fr)
    if not data:
        sys.exit("no captures")
    common = min(fr[-1]["tic_end"] for _, fr in data.values())   # same tic range for every variant
    out = ["# R69 window matrix (instrumented PERF, same demo tics 0..%d)" % common, "",
           "| variant | window (samples) | pixels(4x4) | frames | mean vb/frame | FPS eq. | vs w16 |", "|---|---|---:|---:|---:|---:|---:|"]
    ref = None
    table = []
    for name, (r, fr) in sorted(data.items()):
        sel = [f for f in fr if f["tic_end"] <= common]
        tot = sum(f["vb_end"] - f["vb_start"] for f in sel)
        mean = tot / max(1, len(sel))
        table.append((name, r["view"], len(sel), mean))
        if name == "w16-prof": ref = mean
    for name, view, n, mean in table:
        w, h = window(view)
        rel = (100.0 * (ref / mean - 1)) if ref else 0.0
        out.append("| %s | %dx%d (mode %d, crop %d/%d) | %d | %d | %.2f | %.2f | %+.1f%% |" % (
            name, w, h, view[0], view[1], view[2], w * h, n, mean, 60.0 / mean, rel))
    out += ["", "FPS eq. = 60 / mean vblanks per game frame over the common demo prefix; instrumented ROMs, so use ratios, not absolute FPS."]
    (d / "WINDOW-MATRIX.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))

if __name__ == "__main__":
    main(sys.argv[1])
