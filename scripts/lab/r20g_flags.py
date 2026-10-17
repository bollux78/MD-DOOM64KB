#!/usr/bin/env python3
"""Exact R20g 36-ROM matrix; no accidental R4/noinline/diagnostic flags."""
import pathlib,sys
p=pathlib.Path(sys.argv[1])
common={"DOOM_R20_SIGHT_ITERATIVE","DOOM_R20_PIXEL_ADDX","DOOM_R20_TAN_MULS","DOOM_R20_CELLMAP_MEMO"}
common|={"DOOM_R20_HUD_LAZY","DOOM_R20_FPS_LAZY","DOOM_R20_SCALE_MATH","DOOM_R20_BSP_ITERATIVE"}
import json
extras={n:{"DOOM_R20_"+f for f in flags} for n,flags in json.loads((pathlib.Path(__file__).parent/'r20g_matrix.json').read_text()).items()}
for name,extra in extras.items():
    flags=(p/f"flags-doom-md-r20g-{name}.txt").read_text().split()
    actual={f[2:].split("=")[0] for f in flags if f.startswith("-DDOOM_R20_")}
    if actual!=common|extra:raise SystemExit(f"wrong R20 flags in {name}: {actual}")
    required={"-DDOOM_R19_FLAT_DBRA","-DVIEWWINDOWWIDTH=38","-DVIEWWINDOWHEIGHT=22","-DTIMEDEMO","-DDOOM_NO_VSYNC","-DDOOM_CACHE_SLOTS=16","-DDOOM_HUD_DMA_STATUS_ONLY"}
    if not required.issubset(flags):raise SystemExit(f"missing baseline flag in {name}")
print("PASS: exact R20g 36-ROM matrix, R4 and noinline disabled")

actual_names={f.stem.removeprefix("doom-md-r20g-") for f in p.glob("*.bin")}
if actual_names!=set(extras):raise SystemExit("wrong ROM set")
