#!/usr/bin/env python3
"""R90 split A/B: control (R89) vs split captures from r70_capture.py, same job.

usage: r90_split_compare.py OUT.json CONTROL_DIR SPLIT_DIR
Per common tic (frames matched by game tic):
  * upper half (tile rows 0..10, bytes 0..1671): must be byte-identical (same tables, same columns);
  * lower half (tile rows 11..21): pair codes (low bytes) may differ; attribute bytes of the split ROM carry
    palette bit 0x40 on frames rendered in GS_LEVEL; everything else in the attribute bytes is unchanged.
Timing: mean vblanks per frame over the common tic range (same job only; nothing here is a hardware number).
Exit status 1 if the upper half ever differs.
"""
import json, sys
from pathlib import Path

PIXELS, ROWB, SPLIT_TILE = 3344, 152, 11


def load(d):
    d = Path(d)
    recs = [json.loads(l) for l in (d / "frames.jsonl").read_text().splitlines() if l.strip()]
    raw = (d / "frames.bin").read_bytes()
    first, cost, prev = {}, {}, None
    for i, r in enumerate(recs):
        c = None if prev is None else r["vb"] - prev
        prev = r["vb"]
        if r["tic"] not in first:
            first[r["tic"]] = i; cost[r["tic"]] = c
    return recs, raw, first, cost


def main():
    out, cdir, sdir = sys.argv[1:4]
    _, craw, cfirst, ccost = load(cdir)
    _, sraw, sfirst, scost = load(sdir)
    tics = sorted(set(cfirst) & set(sfirst))
    cut = SPLIT_TILE * ROWB
    top_bad, low_codes, attr_on, attr_other, frames_low_diff = [], 0, 0, 0, 0
    for t in tics:
        a = craw[cfirst[t] * PIXELS:(cfirst[t] + 1) * PIXELS]
        b = sraw[sfirst[t] * PIXELS:(sfirst[t] + 1) * PIXELS]
        if a[:cut] != b[:cut]:
            top_bad.append(t)
        d = sum(1 for k in range(cut + 1, PIXELS, 2) if a[k] != b[k])
        low_codes += d; frames_low_diff += d > 0
        hi = [(a[k], b[k]) for k in range(cut, PIXELS, 2)]
        if all(y == (x | 0x40) for x, y in hi):
            attr_on += 1
        elif any(y != x for x, y in hi):
            attr_other += 1
    def mean(cost, ts):
        v = [cost[t] for t in ts if cost.get(t) is not None]
        return sum(v) / len(v) if v else 0.0
    rep = {"common_tics": len(tics), "tic_range": [tics[0], tics[-1]] if tics else None,
           "upper_half_differs": len(top_bad), "first_upper_diffs": top_bad[:20],
           "frames_lower_codes_differ": frames_low_diff, "lower_code_bytes_differ": low_codes,
           "frames_with_pal23_bits": attr_on, "frames_with_other_attr_changes": attr_other,
           "vblanks_per_frame_control": mean(ccost, tics), "vblanks_per_frame_split": mean(scost, tics)}
    c, s = rep["vblanks_per_frame_control"], rep["vblanks_per_frame_split"]
    rep["delta_pct"] = (s / c - 1) * 100 if c else None
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep))
    return 1 if top_bad or not tics else 0


if __name__ == "__main__":
    sys.exit(main())
