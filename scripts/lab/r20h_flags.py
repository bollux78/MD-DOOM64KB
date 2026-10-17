#!/usr/bin/env python3
"""Exact R20h 40-ROM matrix; no accidental R4/noinline/diagnostic flags."""
import pathlib,sys
p=pathlib.Path(sys.argv[1])
common={"DOOM_R20_SIGHT_ITERATIVE","DOOM_R20_PIXEL_ADDX","DOOM_R20_TAN_MULS","DOOM_R20_CELLMAP_MEMO"}
common|={"DOOM_R20_HUD_LAZY","DOOM_R20_FPS_LAZY","DOOM_R20_SCALE_MATH","DOOM_R20_BSP_ITERATIVE"}
import json
extras={n:{"DOOM_R20_"+f for f in flags} for n,flags in json.loads((pathlib.Path(__file__).parent/'r20h_matrix.json').read_text()).items()}
for name,extra in extras.items():
    flags=(p/f"flags-doom-md-r20h-{name}.txt").read_text().split()
    actual={f[2:].split("=")[0] for f in flags if f.startswith("-DDOOM_R20_")}
    if actual!=common|extra:raise SystemExit(f"wrong R20 flags in {name}: {actual}")
    required={"-DDOOM_R19_FLAT_DBRA","-DVIEWWINDOWWIDTH=38","-DVIEWWINDOWHEIGHT=22","-DTIMEDEMO","-DDOOM_NO_VSYNC","-DDOOM_CACHE_SLOTS=16","-DDOOM_HUD_DMA_STATUS_ONLY"}
    if not required.issubset(flags):raise SystemExit(f"missing baseline flag in {name}")
print("PASS: exact R20h 40-ROM matrix, R4 and noinline disabled")

actual_names={f.stem.removeprefix("doom-md-r20h-") for f in p.glob("*.bin")}
if actual_names!=set(extras):raise SystemExit("wrong ROM set")

# Full 2^4 coverage on exactly the V3+color base, with no rejected options.
from itertools import combinations
switches={"DOOM_R20_REG_COLUMNS","DOOM_R20_CACHE_DIRECT","DOOM_R20_FLAT_INLINE","DOOM_R20_TAN32"}
vc={frozenset(flags-{"DOOM_R20_DMA_BATCH","DOOM_R20_COLOR_ROM"}) for n,flags in extras.items() if n.startswith("vc")}
expected={frozenset(c) for k in range(5) for c in combinations(switches,k)}
if vc!=expected or len([n for n in extras if n.startswith("vc")])!=16:raise SystemExit("incomplete factorial matrix")
print("PASS full 2^4 coverage, V3/color controls and no-V3 combination")

rejected={"DOOM_R20_FLAT_UNROLL","DOOM_R20_WALL_HOIST","DOOM_R20_COMPOSITE_HOIST","DOOM_R20_PIXEL_UNROLL","DOOM_R20_HYGIENE","DOOM_R20_SGDK_HEAP","DOOM_R20_VBLANK_VIDEO","DOOM_R20_SPRTEMP_DYNAMIC"}
if any(flags & rejected for flags in extras.values()):raise SystemExit("rejected option enabled")
for name,flags in extras.items():
 if not name.startswith("diag-") and extras.get("diag-"+name)!=flags|{"DOOM_R20_STACKGUARD"}:raise SystemExit("wrong diagnostic partner")
