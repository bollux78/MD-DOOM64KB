#!/usr/bin/env python3
"""R65: non-invasive repeatable DEMO3 PREFIX test (NOT a full timedemo).

Inspect the R60/R64A original non-profiled PERF ROMs through BlastEm RSP.
Every individual BlastEm process is hard-capped at 10000 emulated frames.
Report emulated VBlank-derived FPS (not host elapsed execution time).
Break at I_FinishUpdate entry, read original benchmark counters.
No recompile, no ROM changes and no runtime counters injected.
"""
import argparse, json, pathlib, statistics, sys
from r64a_rsp_capture import RSP, symbols

TICS=(64,128,256)
REQUIRED=("I_FinishUpdate","_g_gametic","_g_vblankCount",
          "bench_frames","bench_start_vb","bench_active")

def symbol_addr(raw, wanted):
    if wanted in raw:
        return raw[wanted]
    # LTO compiler can suffix static symbols, e.g. r22_fb.lto_priv.0.
    matches=[(key,val) for key,val in raw.items()
             if key.startswith(wanted+".") or key=="_"+wanted]
    if len(matches)!=1:
        raise RuntimeError(f"{wanted}: expected 1 symbol, found {matches}")
    print("SYMBOL ALIAS",wanted,matches[0][0],hex(matches[0][1]),flush=True)
    return matches[0][1]

def read_u32(rsp,address):
    return int.from_bytes(rsp.readmem(address,4),"big")

def read_u8(rsp,address):
    return rsp.readmem(address,1)[0]

def measure(binary,elf,blastem,cap):
    raw=symbols(elf)
    s={key:symbol_addr(raw,key) for key in REQUIRED}
    print("SYMBOLS", {k:hex(v) for k,v in s.items()},flush=True)
    rsp=RSP(blastem,binary,cap,120)
    checkpoints=[]
    hits=0
    try:
        print("RSP",rsp.req("qSupported"),flush=True)
        if rsp.req(f"Z0,{s['I_FinishUpdate']:x},2")!="OK":
            raise RuntimeError("Cannot set benchmark sampling breakpoint")
        while hits<800:
            rsp.cont()
            hits+=1
            tic=read_u32(rsp,s["_g_gametic"])
            if tic not in TICS or any(p["tic"]==tic for p in checkpoints):
                continue
            frames=read_u32(rsp,s["bench_frames"])
            start=read_u32(rsp,s["bench_start_vb"])
            now=read_u32(rsp,s["_g_vblankCount"])
            active=read_u8(rsp,s["bench_active"])
            elapsed=(now-start)&0xffffffff
            if not active or elapsed==0:
                raise RuntimeError(f"Benchmark not active at tic {tic}, active={active}, elapsed={elapsed}")
            if not (1<=frames<=tic+2):
                raise RuntimeError(f"Unexpected benchmark frame count {frames} at tic {tic}")
            fps=(frames*60)/elapsed
            row={"tic":tic,"bench_frames":frames,"elapsed_vblanks":elapsed,
                 "fps_unrounded":fps,"fps_x100":(frames*6000+elapsed//2)//elapsed,
                 "seconds":elapsed/60,"break_hit":hits}
            checkpoints.append(row)
            print("PREFIX",json.dumps(row),flush=True)
            if len(checkpoints)==len(TICS):
                return checkpoints
        raise RuntimeError(f"Not all checkpoints reached before 800 I_FinishUpdate stops: {checkpoints}")
    finally:
        rsp.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ref-rom",required=True)
    p.add_argument("--ref-elf",required=True)
    p.add_argument("--candidate-rom",required=True)
    p.add_argument("--candidate-elf",required=True)
    p.add_argument("--blastem",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--repeats",type=int,default=3)
    p.add_argument("--frame-cap",type=int,default=10000)
    args=p.parse_args()
    if args.repeats<3 or args.repeats>5:p.error("3 to 5 repeats")
    if not (1<=args.frame_cap<=10000):p.error("BlastEm cap <= 10000 per run")
    output=pathlib.Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    measurements={"ref":[],"r64a":[]}
    for rep in range(args.repeats):
        for key,binary,elf in (
            ("ref",args.ref_rom,args.ref_elf),
            ("r64a",args.candidate_rom,args.candidate_elf),
        ):
            print(f"RUN {rep+1}/{args.repeats} {key}",flush=True)
            result=measure(binary,elf,args.blastem,args.frame_cap)
            measurements[key].append(result)
    final=[]
    for tic in TICS:
        ref=[run[next(i for i,r in enumerate(run) if r["tic"]==tic)] for run in measurements["ref"]]
        cand=[run[next(i for i,r in enumerate(run) if r["tic"]==tic)] for run in measurements["r64a"]]
        # Determinism check: same demo and same number of rendered frames.
        values={"ref":[r["fps_unrounded"] for r in ref],
                "r64a":[r["fps_unrounded"] for r in cand]}
        fm_ref=statistics.mean(values["ref"])
        fm_can=statistics.mean(values["r64a"])
        row={"tic":tic,
             "frames_ref":sorted(set(r["bench_frames"] for r in ref)),
             "frames_r64a":sorted(set(r["bench_frames"] for r in cand)),
             "ref_fps":values["ref"],"r64a_fps":values["r64a"],
             "ref_mean":fm_ref,"r64a_mean":fm_can,
             "improvement_pct":(fm_can/fm_ref-1)*100,
             "ref_stdev":statistics.stdev(values["ref"]),
             "r64a_stdev":statistics.stdev(values["r64a"])}
        if row["frames_ref"]!=row["frames_r64a"] or len(row["frames_ref"])!=1:
            raise RuntimeError(f"Frame counts differ at tic {tic}: {row}")
        final.append(row)
        print("COMPARE",json.dumps(row,ensure_ascii=False),flush=True)
    result={"type":"DEMO3 PREFIX ONLY — NOT full 2134-frame benchmark",
            "blasterm_frames_per_process_cap":args.frame_cap,
            "clock":"original Mega Drive; emulate VBlank count only",
            "repeats":args.repeats,"samples":measurements,"summary":final}
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("PASS repeated prefix metrics only. Complete DEMO3 requires manual 3x A/B.",flush=True)

if __name__=="__main__":main()
