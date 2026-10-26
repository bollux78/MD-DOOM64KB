#!/usr/bin/env python3
"""R70 A/B comparison of timedemo captures made by r70_capture.py (same demo, same BlastEm parameters).

Usage: r70_compare.py OUT_DIR control=CAPDIR a1=CAPDIR a2=CAPDIR a12=CAPDIR [repeat=CAPDIR ...]
The first label is the control. Frames are matched by game tic (the demo is deterministic, one tic per frame).
  * Pixels: for every common tic the renderer framebuffer (3344 B) of each variant is compared with the control's;
    differing frames are listed with differing byte count, first positions (x,y cells) and max abs difference.
  * Timing: frame period = vblanks between consecutive I_FinishUpdate hits, over the COMMON tic range only.
    Reported: mean/p50/p90/max vblanks per frame, FPS equivalent (60/mean), delta vs control, delta per third of the
    range (reproducibility across demo sections) and paired faster/equal/slower counts. Resolution is one vblank.
  * Labels starting with 'repeat' are a second run of the control used to prove run-to-run determinism.
Nothing here is a hardware measurement.
"""
import json, pathlib, statistics, sys

PIXELS, W, H = 3344, 76, 44


def load(d):
    d = pathlib.Path(d)
    recs = [json.loads(l) for l in (d / "frames.jsonl").read_text().splitlines() if l.strip()]
    raw = (d / "frames.bin").read_bytes()
    assert len(raw) >= PIXELS * len(recs), (d, len(raw), len(recs))
    first, prev_vb, per_tic = {}, None, {}
    for i, r in enumerate(recs):
        cost = None if prev_vb is None else r["vb"] - prev_vb
        prev_vb = r["vb"]
        if r["tic"] not in first:
            first[r["tic"]] = i
            per_tic[r["tic"]] = cost
    return {"recs": recs, "raw": raw, "first": first, "cost": per_tic}


def frame(cap, tic):
    i = cap["first"][tic]
    return cap["raw"][i * PIXELS:(i + 1) * PIXELS]


def pct(sorted_vals, q):
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))] if sorted_vals else 0


def locate(a, b, limit=6):
    """byte index -> cell. Packed layout is 76 bytes per row pair?? keep it neutral: report row-major byte offsets."""
    diffs = [k for k in range(PIXELS) if a[k] != b[k]]
    return diffs[:limit], len(diffs), max((abs(a[k] - b[k]) for k in diffs), default=0)


def main(out, specs):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    labels = [s.split("=", 1)[0] for s in specs]
    caps = {s.split("=", 1)[0]: load(s.split("=", 1)[1]) for s in specs}
    control = labels[0]
    tic_sets = [set(c["first"]) for c in caps.values()]
    common = sorted(set.intersection(*tic_sets))
    # drop the first common tic: its cost depends on the previous (non common) frame in some captures
    common = [t for t in common if all(caps[l]["cost"].get(t) is not None for l in labels)]
    res = {"labels": labels, "common_tics": len(common),
           "tic_range": [common[0], common[-1]] if common else None, "variants": {}}
    L = ["# R70-A A/B comparison", "",
         "Control: `%s`. Common tics: %d%s. Frames matched by game tic; pixels are the real renderer framebuffer (3344 B), not ROM hashes."
         % (control, len(common), (" (%d..%d)" % (common[0], common[-1])) if common else ""), "",
         "## Capture coverage", "", "| label | frames | first tic | last tic | last vblank |", "|---|---:|---:|---:|---:|"]
    for l in labels:
        r = caps[l]["recs"]
        L.append("| %s | %d | %d | %d | %d |" % (l, len(r), r[0]["tic"], r[-1]["tic"], r[-1]["vb"]))
    if not common:
        L += ["", "**No common tics: nothing to compare.**"]
        (out / "REPORT.md").write_text("\n".join(L) + "\n"); (out / "summary.json").write_text(json.dumps(res, indent=1)); return 1
    thirds = [common[k * len(common) // 3:(k + 1) * len(common) // 3] for k in range(3)]
    base_cost = [caps[control]["cost"][t] for t in common]
    base_total = sum(base_cost)
    L += ["", "## Timing over the common tic range", "",
          "| label | total vblanks | mean vb/frame | FPS eq. | delta vs control | thirds (1/2/3) | p50 | p90 | max | faster/equal/slower frames |",
          "|---|---:|---:|---:|---:|---|---:|---:|---:|---|"]
    for l in labels:
        cost = [caps[l]["cost"][t] for t in common]
        tot = sum(cost); mean = tot / len(cost); srt = sorted(cost)
        d = 100.0 * (tot - base_total) / base_total
        th = []
        for seg in thirds:
            b = sum(caps[control]["cost"][t] for t in seg); v = sum(caps[l]["cost"][t] for t in seg)
            th.append(100.0 * (v - b) / b if b else 0.0)
        fast = sum(1 for x, y in zip(cost, base_cost) if x < y); eq = sum(1 for x, y in zip(cost, base_cost) if x == y)
        slow = len(cost) - fast - eq
        res["variants"][l] = {"total_vb": tot, "mean_vb": mean, "fps_eq": 60.0 / mean, "delta_pct": d, "thirds_pct": th,
                              "p50": pct(srt, .5), "p90": pct(srt, .9), "max": srt[-1], "faster": fast, "equal": eq, "slower": slow}
        L.append("| %s | %d | %.3f | %.2f | %+.2f%% | %s | %d | %d | %d | %d/%d/%d |" % (
            l, tot, mean, 60.0 / mean, d, " / ".join("%+.2f%%" % x for x in th), pct(srt, .5), pct(srt, .9), srt[-1], fast, eq, slow))
    L += ["", "Delta is vblanks (negative = faster). One vblank is the measurement resolution of a single frame; the totals above "
              "aggregate %d frames. Differences below about 0.3%% should be treated as noise-level until confirmed on hardware." % len(common)]
    L += ["", "## Pixel equivalence (renderer framebuffer, common tics)", "",
          "| label | tics compared | identical frames | differing frames | differing bytes (total) | verdict |", "|---|---:|---:|---:|---:|---|"]
    details = []
    for l in labels[1:]:
        same = diff = tbytes = 0
        for t in common:
            a, b = frame(caps[control], t), frame(caps[l], t)
            if a == b:
                same += 1
            else:
                diff += 1
                pos, n, mx = locate(a, b); tbytes += n
                if len(details) < 40:
                    details.append((l, t, n, mx, pos))
        verdict = "IDENTICAL" if diff == 0 else "DIFFERS"
        if l.startswith("repeat"):
            verdict += " (run-to-run determinism of the control)"
        res["variants"][l].update({"identical_frames": same, "differing_frames": diff, "differing_bytes": tbytes})
        L.append("| %s | %d | %d | %d | %d | %s |" % (l, len(common), same, diff, tbytes, verdict))
    if details:
        L += ["", "### Differing frames (first 40): variant, tic, differing bytes, max abs diff, first byte offsets (row-major in the 76x44 buffer)", ""]
        for l, t, n, mx, pos in details:
            L.append("- %s tic %d: %d bytes differ, max |diff| %d, offsets %s (x,y) %s" % (
                l, t, n, mx, pos, [(p % W, p // W) for p in pos]))
    # vblank sequence determinism for repeat runs
    for l in labels:
        if l.startswith("repeat"):
            same_vb = all(caps[l]["cost"][t] == caps[control]["cost"][t] for t in common)
            L.append("")
            L.append("Run-to-run: `%s` vblank sequence %s the control's over the common range." % (l, "EQUALS" if same_vb else "DIFFERS FROM"))
            res["variants"][l]["same_vblank_sequence"] = same_vb
    cand = [l for l in labels[1:] if not l.startswith("repeat")]
    ok = [l for l in cand if res["variants"][l]["differing_frames"] == 0]
    L += ["", "## Reading", ""]
    for l in cand:
        v = res["variants"][l]
        flag = []
        if v["differing_frames"]: flag.append("PIXEL DIFFERENCES: not acceptable as an exact optimisation")
        if any(x > 0.5 for x in v["thirds_pct"]): flag.append("a third of the demo got slower by more than 0.5%")
        L.append("- `%s`: %+.2f%% vblanks vs control, thirds %s; %s" % (
            l, v["delta_pct"], " / ".join("%+.2f%%" % x for x in v["thirds_pct"]), "; ".join(flag) if flag else "no visual difference, no third regressed"))
    faster = [l for l in ok if res["variants"][l]["delta_pct"] < 0]       # pixel-identical AND strictly faster than the control
    if faster:
        best = min(faster, key=lambda l: res["variants"][l]["total_vb"])
        res["best_pixel_identical"] = best
        L.append("")
        L.append("Fastest pixel-identical variant on this capture: `%s` (%+.2f%%). Combinations are not preferred by default: "
                 "if one component alone beats the combination, that one is the candidate." % (best, res["variants"][best]["delta_pct"]))
    else:
        res["best_pixel_identical"] = None
        L.append("")
        L.append("No variant is both pixel-identical and faster than the control (delta < 0); none is called fastest. "
                 "Pixel-identical but not faster: %s." % (", ".join("`%s` (%+.2f%%)" % (l, res["variants"][l]["delta_pct"]) for l in ok) or "none"))
    (out / "REPORT.md").write_text("\n".join(L) + "\n")
    (out / "summary.json").write_text(json.dumps(res, indent=1))
    print("\n".join(L))
    return 0 if all(res["variants"][l]["differing_frames"] == 0 for l in labels[1:]) else 2


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2:]))
