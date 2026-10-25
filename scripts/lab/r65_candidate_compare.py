#!/usr/bin/env python3
"""Read-only six-run R64A vs R65-P1 DEMO3 prefix FPS comparison.

Uses the *original* non-instrumented ROMs and m68k VBlank counters through
the BlastEm RSP debug port. Each invocation has a strict <=10000-frame cap.
This is NOT the complete 2134-frame DEMO3.
"""
import argparse,json,pathlib,statistics
from r65_repeat_prefix import measure

def main():
    p=argparse.ArgumentParser()
    for key in ("r64a_rom","r64a_elf","r65_rom","r65_elf","blastem","output"):
        p.add_argument("--"+key.replace("_","-"),required=True)
    p.add_argument("--repeats",type=int,default=3)
    p.add_argument("--frame-cap",type=int,default=10000)
    a=p.parse_args()
    if a.repeats!=3:p.error("R65-P1 protocol: exactly 3 repeats of each ROM")
    if not 1<=a.frame_cap<=10000:p.error("BlastEm per-process cap <=10000")
    samples={"r64a":[],"r65":[]}
    for i in range(a.repeats):
        for key,rom,elf in (("r64a",a.r64a_rom,a.r64a_elf),
                            ("r65",a.r65_rom,a.r65_elf)):
            print(f"R65-P1 RUN {i+1}/{a.repeats} {key}",flush=True)
            samples[key].append(measure(rom,elf,a.blastem,a.frame_cap))
    report=[]
    for tic in (64,128,256):
        rows={}
        for key in samples:
            rows[key]=[next(x for x in run if x["tic"]==tic)
                       for run in samples[key]]
        frames={key:sorted({x["bench_frames"] for x in rows[key]})
                for key in rows}
        if frames["r64a"]!=frames["r65"] or len(frames["r64a"])!=1:
            raise RuntimeError(f"Different frame counts at tic {tic}: {frames}")
        fps={key:[x["fps_unrounded"] for x in rows[key]]
             for key in rows}
        mean_a=statistics.mean(fps["r64a"])
        mean_b=statistics.mean(fps["r65"])
        row={"tic":tic,"frames":frames["r64a"][0],
             "fps_r64a":fps["r64a"],"fps_r65":fps["r65"],
             "mean_r64a":mean_a,"mean_r65":mean_b,
             "gain_pct":100*(mean_b/mean_a-1),
             "stdev_r64a":statistics.stdev(fps["r64a"]),
             "stdev_r65":statistics.stdev(fps["r65"])}
        report.append(row)
        print("R65-COMPARE",json.dumps(row),flush=True)
    result={"scope":"PREFIX of DEMO3 ONLY, at tics 64/128/256",
            "not_full_benchmark":True,
            "clock":"original 68000 7.67 MHz (simulated hardware)",
            "max_blastem_frames_per_invocation":a.frame_cap,
            "measurements":samples,"summary":report}
    path=pathlib.Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print("SUCCESS: R65-P1 triple prefix comparison; manual full DEMO3 still required")

if __name__=="__main__":
    main()
