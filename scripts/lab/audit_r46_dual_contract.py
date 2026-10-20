#!/usr/bin/env python3
"""R46 M1 preflight: report the compile-time splits blocking genuine dual rendering.
This is an *audit*, not a runtime 8x8/4x4 implementation.

Use fish: python3 scripts/lab/audit_r46_dual_contract.py
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def source(name):
    return (ROOT / name).read_text(encoding="utf-8")

video = source("src/i_genesisv.c")
p4 = source("src/r22_video.inc")
geom = source("src/r_draw.c")
planes = source("src/r_plane.c")
entry = source("src/d_main.c")
build = source("scripts/build_silent.fish")
hud = source("src/wi_libt.c")
r45 = source("scripts/lab/build_r35_linear.fish")
r43 = source("scripts/lab/gen_r43_gray.py")

checks = {
    "exclusive_video_compile_time": video.startswith("#if defined(DOOM_R22_PIXEL4)\n#include \"r22_video.inc\""),
    "pixel4_requires_76x44": "#if VIEWWINDOWWIDTH != R22_W || VIEWWINDOWHEIGHT != R22_H" in p4,
    "pixel4_rejects_cell_asm": "#error Tile-word kernels and the old tilemap hash" in p4,
    "build_rewrites_geometry": all(t in build for t in ("-DVIEWWINDOWWIDTH=76", "-DVIEWWINDOWHEIGHT=44", "-DMAPWIDTH=76")),
    "geom_projection_width_specialized": "#if VIEWWINDOWWIDTH == 76" in geom and "#elif VIEWWINDOWWIDTH == 38" in geom,
    "geom_clip_arrays_static": "floorclip[VIEWWINDOWWIDTH]" in geom and "ceilingclip[VIEWWINDOWWIDTH]" in geom,
    "pixel4_openings_heap": "R22_InitOpenings" in geom and "R22_Alloc(MAXOPENINGS" in geom,
    "planes_height_specialized": "yslopeTable[VIEWWINDOWHEIGHT / 2]" in planes,
    "planes_width_specialized": "distscaleTable[VIEWWINDOWWIDTH]" in planes,
    "frame_entry_pixel4_conditional": "#if defined(DOOM_R22_PIXEL4)" in entry and "R22_BeginFrame();" in entry,
    "intermission_text_coordinates_fixed": "WI_TEXT_WIDTH 38" in hud and "WI_TEXT_HEIGHT 22" in hud,
    "R39f_tri_dither_preserved": "DOOM_R39F_DITHER3" in r45 and "R39F_SetDitherMode" in video,
    "R44_asm_separate": "R42_DrawPackedWall" in p4 and "DOOM_R42_WALL_ASM" in p4,
    "R43_optional_only": "DOOM_R43_GRAY_CRT" in r45 and "r43_gray_palette.h" in p4 and "gray" in r43.lower(),
}
assert all(checks.values()), {k: v for k, v in checks.items() if not v}

report = {
    "milestone": "R46/M1 preflight, does not implement runtime switching",
    "from_branch": "r45-merged-asm-gray-controls",
    "modes": {
        "cell8": {"columns": 38, "rows": 22, "samples": 836, "hud_tilemap_buffer_bytes": 38 * 28 * 2, "vdptiles_solid_checker_vertical": 16 + 105 + 105},
        "pixel4": {"columns": 76, "rows": 44, "samples": 3344, "framebuffer_bytes": 76 * 44 // 2, "row_stride_bytes": 38,
                    "tilemap_words": 38 * 21, "tilemap_bytes": 38 * 21 * 2,
                    "tile_banks": 2, "vdptiles_per_bank": 836,
                    "antiflicker_alias_bytes": 2 * ((38 * 22 + 7) // 8)}
    },
    "critical_boundaries": [
        "src/i_genesisv.c: compile-time exclusive video backend, shared external symbols",
        "src/r_draw.c: geometry projection tables, clipping arrays and R22 heap openings tied to build-wide WIDTH/HEIGHT",
        "src/r_plane.c: per-mode slopes, distscale and spans tied to compile-time WIDTH/HEIGHT",
        "src/d_main.c: begin-frame only happens in pixel4 build",
        "src/i_genesis.c: callback calls common R20_VBlankVideo symbol; future dispatch must be atomic with DMA",
        "src/r22_video.inc: R42 asm is native 4bpp only, no reuse of R20 tile-word asm",
        "src/wi_libt.c: 38x22 text grid is independent of native 76x44 samples",
        "R43 gray palette affects all 4x4 3D materials, not only floor and ceiling"
    ],
    "cannot_assume": [
        "both sets of pixel patterns can remain in VRAM simultaneously",
        "two independently compiled full engines fit 64KiB WRAM",
        "menu toggle alone changes projection or data types",
        "R45 controls are runtime dual (all six are separate compile-time backends)"
    ],
    "checks": checks,
    "next_product_gates": [
        "M1 create namespace-isolated dual video entrypoints and budget WRAM/ROM/VRAM for both backends",
        "M2 make projection/clip/plane tables selectable without extra branches in innermost loops; preserve 38x22 and 76x44",
        "M3 queue swaps and coordinate DMA, ISR, palette, font, HUD and native static text",
        "M4 add Options Render: 8x8/4x4 and verify same live E1M1 state is preserved"
    ]
}

parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path)
args = parser.parse_args()
out = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
if args.out:
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out, encoding="utf-8")
print(out)
