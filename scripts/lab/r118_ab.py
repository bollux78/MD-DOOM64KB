#!/usr/bin/env python3
"""Rendered-timing A/B on the R116 demos from r117_profile.py runs (R121: strict version).

Usage: r118_ab.py OUT.json label=DIR [label=DIR ...]   (first label = control; DIR/dK-ab/{frames.tsv,PROFILE.json})
For each demo, the common tic range [A, B] is timed as VBlanks(frame at tic B) - VBlanks(frame at tic A).

R121 diagnosis of the R120 "+167%": in run 41726158554 the CONTROL runs of demos 3/7/9 were executed by a BlastEm
whose 68000 ran exactly 7x faster (VBlanks to reach tic 151: 137 vs 946; rendered range 551 vs 3855 VBlanks;
ratios 6.88-7.00; demo 10, run a little later: 1.00). 7 = BlastEm clocks.m68k_divider 7 -> 1: the runner's BlastEm
read a user-level config with the 68000 overclocked. The candidates were right; the control was not comparable.
Checks now (any failure -> INVALID, exit code 1):
  - every run present, status frame_limit/demo_end, >= 50 common tics, no load (leveltime discontinuity) inside the range;
  - identical leveltime for every common tic (same game state; logic identity is checked elsewhere too);
  - emulator-speed calibration (PROFILE.json from the R121 profiler): VBlanks from boot to the first G_Ticker
    (boot_vb) within +-5% of the control; logic-only skip phase within +-25% (logic speed-ups change it legitimately).
    Old profiles without boot_vb: fallback check on the VBlank count of the first common tic (within +-25%).
"""
import json, pathlib, sys


def load(p):
    rows = [tuple(int(x) for x in l.split("\t")) for l in pathlib.Path(p).read_text().splitlines() if l.strip()]
    vb, lt = {}, {}
    for v, t, l in rows: vb[t] = v; lt[t] = l          # last frame of each tic (one frame per tic in timedemo)
    return vb, lt


def main():
    out = sys.argv[1]; runs = [a.split("=", 1) for a in sys.argv[2:]]; ctl = runs[0][0]
    demos = sorted({int(d.name[1:].split("-")[0]) for _, r in runs for d in pathlib.Path(r).glob("d*-ab")})
    res = {"control": ctl, "demos": {}, "invalid": []}; tot = {l: 0 for l, _ in runs}
    for k in demos:
        F, L, P, bad = {}, {}, {}, []
        for l, r in runs:
            d = pathlib.Path(r) / ("d%d-ab" % k)
            try:
                F[l], L[l] = load(d / "frames.tsv"); P[l] = json.loads((d / "PROFILE.json").read_text())
            except Exception as e:
                bad.append("%s: missing (%s)" % (l, e)); continue
            if P[l].get("status") not in ("frame_limit", "demo_end"): bad.append("%s: status %s" % (l, P[l].get("status")))
            if len(F[l]) < 50: bad.append("%s: only %d frames" % (l, len(F[l])))
        if not bad:
            a = max(min(f) for f in F.values()) + 1; b = min(max(f) for f in F.values())
            common = [t for t in range(a, b + 1) if all(t in f for f in F.values())]
            if len(common) < 50: bad.append("only %d common tics" % len(common))
            else:
                a, b = common[0], common[-1]
                cb = P[ctl].get("boot_vb")
                for l in F:
                    if cb:
                        bv = P[l].get("boot_vb"); cs = P[ctl]["skip_end_vb"] - cb; sk = (P[l].get("skip_end_vb") or 0) - (bv or 0)
                        if not bv or abs(bv / cb - 1) > 0.05: bad.append("%s: boot_vb %s vs control %s (emulator speed?)" % (l, bv, cb))
                        elif cs > 0 and abs(sk / cs - 1) > 0.25: bad.append("%s: skip phase %d vs control %d VBlanks" % (l, sk, cs))
                    elif abs(F[l][a] / F[ctl][a] - 1) > 0.25:
                        bad.append("%s: %d VBlanks to reach tic %d vs control %d (emulator speed?)" % (l, F[l][a], a, F[ctl][a]))
                    if any(L[l][t] != L[ctl][t] for t in common): bad.append("%s: leveltime differs from control" % l)
                    gaps = [t for t in common[1:] if t - 1 in L[l] and L[l][t] != L[l][t - 1] + 1]
                    if gaps: bad.append("%s: load (leveltime discontinuity) inside range at tics %s" % (l, gaps[:5]))
        if bad:
            res["demos"][k] = {"invalid": bad}; res["invalid"].append(k); continue
        vb = {l: F[l][b] - F[l][a] for l in F}
        res["demos"][k] = {"tics": [a, b], "vblanks": vb, "delta_pct": {l: round((v / vb[ctl] - 1) * 100, 2) for l, v in vb.items()},
                           "boot_vb": {l: P[l].get("boot_vb") for l in P}}
        for l in vb: tot[l] += vb[l]
    c = tot[ctl]
    res["total_vblanks"] = tot
    res["total_delta_pct"] = {l: round((v / c - 1) * 100, 2) if c else None for l, v in tot.items()}
    pathlib.Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(("INVALID demos %s; " % res["invalid"] if res["invalid"] else "") + json.dumps(res["total_delta_pct"]))
    for k, v in res["demos"].items(): print(k, v.get("invalid") or (v["tics"], v["delta_pct"]))
    return 1 if res["invalid"] else 0


if __name__ == "__main__":
    sys.exit(main())
