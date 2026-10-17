#!/usr/bin/env python3
"""Require the exact intended experimental matrix, not just matching common flags."""
import pathlib, sys
p=pathlib.Path(sys.argv[1])
common={"DOOM_R20_SIGHT_ITERATIVE", "DOOM_R20_NOINLINE_COLUMNS"}
extras={"control":set(), "p2":{"DOOM_R20_PIXEL_ADDX"},
"m1":{"DOOM_R20_TAN_MULS"}, "combo":{"DOOM_R20_PIXEL_ADDX","DOOM_R20_TAN_MULS"},
"diag":{"DOOM_R20_PIXEL_ADDX","DOOM_R20_TAN_MULS","DOOM_R20_STACKGUARD"},
"natural":set()}
for name,extra in extras.items():
    flags=(p/f"flags-doom-md-r20b-{name}.txt").read_text().split()
    actual={f[2:].split("=")[0] for f in flags if f.startswith("-DDOOM_R20_")}
    expected=({"DOOM_R20_SIGHT_ITERATIVE"} if name=="natural" else common)|extra
    if actual!=expected: raise SystemExit(f"wrong R20 flags for {name}: {actual} vs {expected}")
    required={"-DDOOM_R19_FLAT_DBRA","-DVIEWWINDOWWIDTH=38","-DVIEWWINDOWHEIGHT=22", "-DTIMEDEMO", "-DDOOM_NO_VSYNC", "-DDOOM_CACHE_SLOTS=16"}
    if not required.issubset(flags): raise SystemExit(f"missing baseline flag in {name}")
    forbidden={"-DDOOM_R15_TANMUL","-DDOOM_R13_MUL_DECOMP","-DDOOM_ROUTINE_PROFILE","-DDOOM_CACHE_STATS"}
    if forbidden.intersection(flags): raise SystemExit(f"unwanted flag in {name}")
print("PASS: exact R20b six-ROM matrix and common baseline")
