#!/usr/bin/env python3
"""Exact R20f four-ROM matrix; no accidental R4/noinline/diagnostic flags."""
import pathlib,sys
p=pathlib.Path(sys.argv[1])
common={"DOOM_R20_SIGHT_ITERATIVE","DOOM_R20_PIXEL_ADDX","DOOM_R20_TAN_MULS","DOOM_R20_CELLMAP_MEMO"}
allflags={"DOOM_R20_HUD_LAZY","DOOM_R20_FPS_LAZY","DOOM_R20_SCALE_MATH","DOOM_R20_BSP_ITERATIVE"}
extras={"control":set(),"hud":{"DOOM_R20_HUD_LAZY"},"all":allflags,"diag":allflags|{"DOOM_R20_STACKGUARD"}}
for name,extra in extras.items():
    flags=(p/f"flags-doom-md-r20f-{name}.txt").read_text().split()
    actual={f[2:].split("=")[0] for f in flags if f.startswith("-DDOOM_R20_")}
    if actual!=common|extra:raise SystemExit(f"wrong R20 flags in {name}: {actual}")
    required={"-DDOOM_R19_FLAT_DBRA","-DVIEWWINDOWWIDTH=38","-DVIEWWINDOWHEIGHT=22","-DTIMEDEMO","-DDOOM_NO_VSYNC","-DDOOM_CACHE_SLOTS=16","-DDOOM_HUD_DMA_STATUS_ONLY"}
    if not required.issubset(flags):raise SystemExit(f"missing baseline flag in {name}")
print("PASS: exact R20f four-ROM matrix, R4 and noinline disabled")
