#!/usr/bin/env python3
"""S1e deterministic logic checkpoint comparison, for future real sub-CPU traces.

Both CSVs must contain:
tic,player_x,player_y,player_z,angle,health,mobjs,prndindex
The MD G_Ticker and sub P_Ticker observers emit independent checkpoints. Never synthesize
or infer the sub trace from the MD trace. Exit 0 when traces valid even if
divergent: playable behavior is the acceptance criterion, not bit identity.
"""
import argparse
import csv
import json
from pathlib import Path

FIELDS = ("tic", "player_x", "player_y", "player_z", "angle",
          "health", "mobjs", "prndindex")

def load(path):
    with Path(path).open(newline="") as fp:
        rows = csv.DictReader(fp)
        if not rows.fieldnames or any(x not in rows.fieldnames for x in FIELDS):
            raise ValueError(f"{path}: missing fields from {FIELDS}")
        trace = {}
        for row in rows:
            x = {key: int(row[key], 0) for key in FIELDS}
            tic = x["tic"]
            if tic in trace or tic < 0 or tic > 2600 or tic % 100:
                raise ValueError(f"{path}: invalid/duplicate checkpoint {tic}")
            trace[tic] = x
    if set(trace)!=set(range(0,2601,100)):
        raise ValueError(f"{path}: require all 27 checkpoints from 0 through 2600")
    return trace

def compare(md, sub):
    md_tics, sub_tics = set(md), set(sub)
    first = None
    differences = []
    for tic in sorted(md_tics | sub_tics):
        fields = []
        if tic not in md or tic not in sub:
            fields = ["missing_md" if tic not in md else "missing_sub"]
        else:
            fields = [f for f in FIELDS[1:] if md[tic][f] != sub[tic][f]]
        if fields:
            differences.append({"tic": tic, "fields": fields})
            if first is None:
                first = tic
    return {"md_checkpoints": len(md), "sub_checkpoints": len(sub),
            "first_divergent_tic": first, "differences": differences,
            "exact_match": not differences,
            "sampling": "First divergence means checkpoint (100-tic spacing), not exact simulation tic.",
            "first_dead_checkpoint_md": next((t for t in sorted(md) if md[t]["health"]<=0),None),
            "first_dead_checkpoint_sub": next((t for t in sorted(sub) if sub[t]["health"]<=0),None),
            "first_divergent_states": ({"md":md.get(first),"sub":sub.get(first)} if first is not None else None)}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("md_csv")
    p.add_argument("sub_csv")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    md, sub = load(args.md_csv), load(args.sub_csv)
    report = compare(md, sub)
    report["disclaimer"] = "Comparison only: does not prove sub-68000 execution. Require independent BlastEm trace."
    print(json.dumps(report),flush=True)
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    print("S1e comparison: checkpoints MD=%d sub=%d, first divergence=%s" %
          (report["md_checkpoints"], report["sub_checkpoints"], report["first_divergent_tic"]))

if __name__ == "__main__":
    main()
