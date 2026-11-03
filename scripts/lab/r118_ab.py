#!/usr/bin/env python3
"""R118: rendered-timing A/B on the R116 demos from r117_profile.py runs (frames.tsv: vblank, gametic, leveltime).

Usage: r118_ab.py OUT.json label=DIR [label=DIR ...]   (first label is the control)
Per demo dir pattern DIR/dK-ab/frames.tsv. For every demo, the common tic range [A, B] (first frame tic +1 ..
smallest last tic over all runs) is timed as VBlanks(frame at tic B) - VBlanks(frame at tic A) in each run.
Logic is identical (checked separately), so the work in [A, B] is identical and the VBlank delta is the speed change.
"""
import json, pathlib, sys


def load(p):
    rows = [tuple(int(x) for x in l.split("\t")) for l in pathlib.Path(p).read_text().splitlines() if l.strip()]
    return {t: vb for vb, t, lt in rows}            # last frame of each tic (one frame per tic in timedemo)


def main():
    out = sys.argv[1]; runs = [a.split("=", 1) for a in sys.argv[2:]]
    demos = sorted({int(d.name[1:].split("-")[0]) for _, r in runs for d in pathlib.Path(r).glob("d*-ab") if (d / "frames.tsv").exists()})
    res = {"control": runs[0][0], "demos": {}}; tot = {l: 0 for l, _ in runs}
    for k in demos:
        F = {}
        for l, r in runs:
            p = pathlib.Path(r) / ("d%d-ab" % k) / "frames.tsv"
            if p.exists(): F[l] = load(p)
        if len(F) != len(runs) or any(len(f) < 20 for f in F.values()): res["demos"][k] = "missing"; continue
        a = max(min(f) for f in F.values()) + 1; b = min(max(f) for f in F.values())
        common = [t for t in range(a, b + 1) if all(t in f for f in F.values())]
        a, b = common[0], common[-1]
        vb = {l: F[l][b] - F[l][a] for l in F}
        c = vb[runs[0][0]]
        res["demos"][k] = {"tics": [a, b], "vblanks": vb, "delta_pct": {l: round((v / c - 1) * 100, 2) for l, v in vb.items()}}
        for l in vb: tot[l] += vb[l]
    c = tot[runs[0][0]]
    res["total_vblanks"] = tot; res["total_delta_pct"] = {l: round((v / c - 1) * 100, 2) if c else None for l, v in tot.items()}
    pathlib.Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["total_delta_pct"]))
    for k, v in res["demos"].items(): print(k, v if isinstance(v, str) else (v["tics"], v["delta_pct"]))


if __name__ == "__main__":
    main()
