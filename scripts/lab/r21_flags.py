#!/usr/bin/env python3
"""R21: every ROM = R20h common + vc-all + exactly its r21_matrix.json extras.
No R20 option rejected in R20h may appear except the two stability probes
(S5 = R20_SGDK_HEAP, V2 = R20_VBLANK_VIDEO) in the variants that name them."""
import json, pathlib, sys
d = pathlib.Path(sys.argv[1]); ids = sys.argv[2:]
m = json.loads((pathlib.Path(__file__).parent / "r21_matrix.json").read_text())
common = {"R20_SIGHT_ITERATIVE", "R20_PIXEL_ADDX", "R20_TAN_MULS", "R20_CELLMAP_MEMO",
          "R20_HUD_LAZY", "R20_FPS_LAZY", "R20_SCALE_MATH", "R20_BSP_ITERATIVE",
          "R20_DMA_BATCH", "R20_COLOR_ROM", "R20_REG_COLUMNS", "R20_CACHE_DIRECT",
          "R20_FLAT_INLINE", "R20_TAN32"}
rejected = {"R20_FLAT_UNROLL", "R20_WALL_HOIST", "R20_COMPOSITE_HOIST", "R20_PIXEL_UNROLL",
            "R20_HYGIENE", "R20_SPRTEMP_DYNAMIC", "R20_SGDK_HEAP", "R20_VBLANK_VIDEO"}
required = {"-DDOOM_R19_FLAT_DBRA", "-DVIEWWINDOWWIDTH=38", "-DVIEWWINDOWHEIGHT=22", "-DTIMEDEMO",
            "-DDOOM_NO_VSYNC", "-DDOOM_CACHE_SLOTS=16", "-DDOOM_HUD_DMA_STATUS_ONLY"}
base_other = None
for i in ids:
    name = i.removeprefix("doom-md-r21-")
    flags = (d / f"flags-{i}.txt").read_text().split()
    actual = {f[7:].split("=")[0] for f in flags if f.startswith(("-DDOOM_R20_", "-DDOOM_R21_"))}
    want = common | set(m[name])
    if actual != want:
        raise SystemExit(f"{i}: R20/R21 flags {sorted(actual ^ want)} differ from the matrix")
    if (actual & rejected) - set(m[name]):
        raise SystemExit(f"{i}: rejected R20 option enabled")
    if not required.issubset(flags):
        raise SystemExit(f"{i}: missing baseline flag")
    other = sorted(f for f in flags if not f.startswith(("-DDOOM_R20_", "-DDOOM_R21_", "doom-md-")))
    if base_other is None:
        base_other = other
    elif other != base_other:
        raise SystemExit(f"{i}: non-R20/R21 compiler flags differ from the first ROM")
print(f"PASS: {len(ids)} ROMs = R20h common + vc-all + their r21_matrix.json extras")
