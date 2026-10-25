#!/usr/bin/env python3
"""R67: repeated unbiased prefix benchmark of R66 reference vs lossy G4/G8/G16.

Only small DEMO3 prefix windows at 64/128/256 ticks are tested automatically.
Each invocation of BlastEm stays below 10000 emulated frames.
Do not conflate these measurements with complete 2134-frame DEMO3.
"""
import argparse
import json
import pathlib
import statistics
from r65_repeat_prefix import measure

NAMES=("r66-perf","r67-g4-perf","r67-g8-perf","r67-g16-perf")
CHECKS=(64,128,256)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--roms", required=True)
    p.add_argument("--blastem",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--repeat",type=int,default=3)
    p.add_argument("--cap",type=int,default=10000)
    args=p.parse_args()
    if not (args.repeat == 3 and 1<=args.cap<=10000):
        p.error("Exactly 3 runs per variant, BlastEm frame cap 1..10000")
    base=pathlib.Path(args.roms)
    outputs={name:[] for name in NAMES}
    for rep in range(args.repeat):
        for name in NAMES:
            stem=base/("doom-md-r60-"+name)
            print(f"REPEAT {rep+1}/3 {name}",flush=True)
            run=measure(str(stem.with_suffix(".bin")),str(stem.with_suffix(".elf")),args.blastem,args.cap)
            outputs[name].append(run)
    summary=[]
    for tic in CHECKS:
        values={}
        frame_counts={}
        for name in NAMES:
            rows=[next(row for row in run if row["tic"]==tic) for run in outputs[name]]
            values[name]=[row["fps_unrounded"] for row in rows]
            frame_counts[name]=sorted({row["bench_frames"] for row in rows})
        if len({tuple(v) for v in frame_counts.values()})!=1:
            raise RuntimeError(f"Rendered frame counts differ: {tic} {frame_counts}")
        ref=statistics.mean(values["r66-perf"])
        for candidate in NAMES[1:]:
            m=statistics.mean(values[candidate])
            summary.append({"tic":tic,"candidate":candidate,
                            "r66_mean_fps":ref,"candidate_mean_fps":m,
                            "gain_vs_r66_pct":(m/ref-1)*100,
                            "candidate_runs":values[candidate],
                            "reference_runs":values["r66-perf"],
                            "candidate_stdev":statistics.stdev(values[candidate]),
                            "reference_stdev":statistics.stdev(values["r66-perf"])})
            print("R67_COMP",json.dumps(summary[-1],ensure_ascii=False),flush=True)
    out=pathlib.Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"scope":"DEMO3 prefix only, not complete 2134 frames",
                               "clock":"NTSC stock ~7.67 MHz","samples":outputs,
                               "summary":summary},indent=2)+"\n")
    print("PASS non-instrumented R66/G4/G8/G16 3x results only; full benchmark pending",flush=True)
if __name__ == "__main__":
    main()
