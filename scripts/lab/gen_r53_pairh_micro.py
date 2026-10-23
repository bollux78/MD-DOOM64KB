#!/usr/bin/env python3
"""Generate a deterministic 25% Pair-H palette-local microdither partner map.

The baseline R22 single palette and 76x44 framebuffer remain unchanged.
Companions are selected offline by reducing RGB error against PLAYPAL index
groups represented by each R22 palette slot. This is an experimental heuristic,
not the R53 Claudio dual-palette optimizer.
"""
from __future__ import annotations
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "src/r22_palette.h"
OUT = ROOT / "src/r53_pairh_micro_tables.h"
REPORT = ROOT / "src/r53_pairh_micro_report.json"

def read_arrays():
    src = HEADER.read_text()
    m = re.search(r"r22_color\[256\]=\{([^}]+)\}", src)
    p = re.search(r"r22_cram\[14\]\[16\]=\{\s*\{([^}]+)\}", src)
    assert m and p, "R22 palette format changed"
    index = [int(x) for x in m.group(1).split(",")]
    words = [int(x) for x in p.group(1).split(",")]
    assert len(index) == 256 and len(words) == 16
    assert all(0 <= x < 16 for x in index)
    return index, words

def to_linear(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

def to_srgb(v):
    v = max(0.0, min(1.0, v))
    return 255.0 * (12.92 * v if v <= 0.0031308 else 1.055 * v ** (1.0 / 2.4) - 0.055)

def mix(base, companion, share=0.25):
    return tuple(to_srgb((1-share)*to_linear(a)+share*to_linear(b))
                 for a,b in zip(base,companion))

def err(target, color):
    return sum((a-b)**2 for a,b in zip(target,color))

def luma(rgb):
    return 0.2126*rgb[0] + 0.7152*rgb[1] + 0.0722*rgb[2]

def main():
    gp = runpy.run_path(str(ROOT / "scripts/genpal.py"))
    source = gp["decode_subpal"](gp["load_playpal"](), 0)
    indices, words = read_arrays()
    colors = [gp["gen_to_rgb"](word) for word in words]
    partner = list(range(16))
    accepted = []
    for i in range(1,16):
        group = [source[k] for k in range(256) if indices[k] == i]
        if not group:
            continue
        original = sum(err(rgb, colors[i]) for rgb in group)
        best = original
        chosen = i
        for j in range(1,16):
            if i == j:
                continue
            contrast = err(colors[i],colors[j]) ** 0.5
            if contrast > 110 or abs(luma(colors[i])-luma(colors[j])) > 48:
                continue
            blended = mix(colors[i],colors[j])
            candidate = sum(err(rgb,blended) for rgb in group)
            if candidate < best:
                best,chosen = candidate,j
        if chosen != i and original-best > max(1.0, original*0.012):
            partner[i] = chosen
            accepted.append({"slot":i,"companion":chosen,
                             "original_sse":round(original,2),
                             "micro_sse":round(best,2),
                             "source_indices":len(group)})
    assert partner[0] == 0
    assert all(0 <= p < 16 for p in partner)
    OUT.write_text("/* Generated: 25% Pair-H local palette microdither. */\n"
                   "#ifndef R53_PAIRH_MICRO_TABLES_H\n"
                   "#define R53_PAIRH_MICRO_TABLES_H\n"
                   "#include <stdint.h>\n"
                   "static const uint8_t r53_pairh_partner[16]={"
                   + ",".join(map(str,partner)) + "};\n"
                   "#endif\n")
    REPORT.write_text(json.dumps({
        "mode":"Pair-H", "ratio_percent":25,
        "baseline_palette":"r22_cram[0]", "palette_slots":16,
        "method":"per-slot uniform-PLAYPAL-index SSE; linear-light 25% blend; contrast/luma gate",
        "companion_map":partner, "active_count":len(accepted),
        "accepted":accepted,
        "note":"Experimental heuristic, NOT R53 Claudio palette; static 256 tiles, no runtime cost."
    },indent=2)+"\n")
    print("Pair-H 25% companions:",partner,"active:",len(accepted))
    if not accepted:
        raise SystemExit("No useful microdither companions: refuse no-op build")

if __name__ == "__main__":
    main()
