#!/usr/bin/env python3
"""MAME batch benchmark. Outputs real in-game bench_frames/bench_vints, not host speed."""
import argparse, os, re, shutil, subprocess, json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("--rom",type=Path,required=True)
p.add_argument("--symbols",type=Path,required=True)
p.add_argument("--mode",type=int,choices=(1,2),required=True)
p.add_argument("--result",type=Path,required=True)
args=p.parse_args()

symbols=json.loads(args.symbols.read_text())
keys=("bench_req","bench_done","bench_frames","bench_vints")
assert all(k in symbols for k in keys),[k for k in keys if k not in symbols]
env=os.environ.copy()
for k in keys:env["DREAD_"+k.upper()]=str(symbols[k])
env["DREAD_BENCH_MODE"]=str(args.mode)
exe=shutil.which("mame") or "/usr/games/mame"
script=Path(__file__).with_suffix(".lua").resolve()
cmd=[exe,"megadriv","-cart",str(args.rom.resolve()),"-video","none",
     "-sound","none","-nothrottle","-seconds_to_run","145",
     "-skip_gameinfo","-autoboot_script",str(script)]
args.result.parent.mkdir(parents=True,exist_ok=True)
print("Running MAME NTSC DEMO3 E1M7 smoke-test; AI active="+str(args.mode==2),flush=True)
try:
    run=subprocess.run(cmd,env=env,text=True,stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,timeout=260)
    output=run.stdout
except subprocess.TimeoutExpired as e:
    output=(e.stdout or b"").decode(errors="replace") if isinstance(e.stdout,bytes) else e.stdout or ""
    run=type("Failed",(),{"returncode":124})()
(args.result.parent/(f"mame-mode{args.mode}.log")).write_text(output)
print("\n".join(x for x in output.splitlines() if "DREAD_" in x)[-4500:],flush=True)
m=re.search(r"DREAD_BENCH_RESULT mode=(\d+) frames=(\d+) vblanks=(\d+) fps_x1000=(\d+)",output)
assert m,(args.rom,args.mode,run.returncode,output[-1800:])
mode,frames,vblanks,fps1000=map(int,m.groups())
assert mode==args.mode and frames>=200 and vblanks>frames and fps1000>0,(mode,frames,vblanks,fps1000)
# VBlanks per game frame: how many frames took 1, 2, 3... VBlanks (quantisation shows here)
h=re.search(r"DREAD_BENCH_HIST ([0-9x,]+)",output)
hist={}
if h:
    for item in h.group(1).split(","):
        d,c=item.split("x")
        hist[int(d)]=int(c)
vh=re.search(r"DREAD_VISUAL_HASH mode=(\d+) hash=(\d+)",output)
visual_hash=int(vh.group(2)) if vh and int(vh.group(1))==mode else None
result={"mode":mode,"type":"combat_with_ai" if mode==2 else "render_without_ai",
        # render (mode 1) runs with AI off: comparable across variants only if AI is unchanged.
        # combat (mode 2) runs with AI on: enemy behaviour differs between AI variants,
        # so the same route is NOT the same workload there. Report AI cost separately.
        "ai_active":mode==2,
        "frames":frames,"vblanks":vblanks,"fps":round(frames*60/vblanks,4),
        "vblanks_per_frame_mean":round(vblanks/frames,3),
        "vblank_histogram":{str(k):v for k,v in sorted(hist.items())},
        "visual_hash":visual_hash,
        "boot_sample_colors":int(re.search(r"DREAD_BOOT_SAMPLED_COLORS=(\d+)",output).group(1))
           if "DREAD_BOOT_SAMPLED_COLORS=" in output else None,
        "mame_returncode":run.returncode}
assert result["boot_sample_colors"] is None or result["boot_sample_colors"]>=4,"Black screen"
args.result.write_text(json.dumps(result,indent=2)+"\n")
print("MEASURED",json.dumps(result),flush=True)
