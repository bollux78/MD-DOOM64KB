#!/usr/bin/env python3
"""Require R20c natural baseline and only the intended R2/R4 experiments."""
import pathlib,sys
p=pathlib.Path(sys.argv[1])
common={"DOOM_R20_SIGHT_ITERATIVE","DOOM_R20_PIXEL_ADDX","DOOM_R20_TAN_MULS"}
extras={"control":set(),"r2":{"DOOM_R20_CELLMAP_MEMO"},"r4":{"DOOM_R20_WALL_HOIST"},
"combo":{"DOOM_R20_CELLMAP_MEMO","DOOM_R20_WALL_HOIST"},
"diag":{"DOOM_R20_CELLMAP_MEMO","DOOM_R20_WALL_HOIST","DOOM_R20_STACKGUARD"}}
for name,extra in extras.items():
    flags=(p/f"flags-doom-md-r20d-{name}.txt").read_text().split()
    actual={f[2:].split("=")[0] for f in flags if f.startswith("-DDOOM_R20_")}
    if actual!=common|extra: raise SystemExit(f"wrong R20 flags in {name}: {actual}")
    required={"-DDOOM_R19_FLAT_DBRA","-DVIEWWINDOWWIDTH=38","-DVIEWWINDOWHEIGHT=22","-DTIMEDEMO","-DDOOM_NO_VSYNC","-DDOOM_CACHE_SLOTS=16"}
    if not required.issubset(flags): raise SystemExit(f"missing baseline flag in {name}")
    forbidden={"-DDOOM_R15_TANMUL","-DDOOM_R13_MUL_DECOMP","-DDOOM_ROUTINE_PROFILE","-DDOOM_CACHE_STATS"}
    if forbidden.intersection(flags): raise SystemExit(f"unexpected baseline flag in {name}")
print("PASS: R20d five-ROM matrix, natural inlining, validated baseline")
