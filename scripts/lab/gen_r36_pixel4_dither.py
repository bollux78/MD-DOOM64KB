#!/usr/bin/env python3
"""R36 Pixel4: 32 virtual 4x4 colors (16 solids + 16 checkerboard blends).

No extra CRAM banks or per-frame RGB math.  The R22 4-bit framebuffer gains
one packed high-bit plane (418 bytes); ROM row LUTs expand pairs of 5-bit codes
directly to Genesis 4bpp in two 8x8-tile scanline phases. All four 4x4 samples
inside one tile still use PAL0, so the VDP bank layout is unchanged.
Generated after scripts/lab/gen_r22_pixel4.py, using the same PLAYPAL source.
"""
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import genpal

PALETTE = ROOT / "src" / "r22_palette.h"
OUTPUT = ROOT / "src" / "r36_pixel4_dither.h"
NPAIRS = 16


def palette_rgb():
    source = PALETTE.read_text(encoding="utf-8")
    found = re.search(r"r22_cram\[14\]\[16\]\s*=\s*\{\s*\{([^}]*)\}", source, re.S)
    if not found:
        raise RuntimeError("R22 palette missing: first run gen_r22_pixel4.py")
    words = [int(n) for n in re.findall(r"\b\d+\b", found.group(1))]
    if len(words) != 16:
        raise RuntimeError("Expected exactly 16 R22 CRAM entries")
    return [genpal.gen_to_rgb(n) for n in words]


def choose_colors(original, solids):
    """Greedy MSE reduction, with small checker contrast penalty."""
    dist = genpal.dist2
    candidates = [(a, b) for a in range(16) for b in range(a + 1, 16)]
    def mean(a, b):
        return tuple((solids[a][k] + solids[b][k]) / 2 for k in range(3))
    def penalty(a, b):
        return 0.018 * dist(solids[a], solids[b])
    base = [min(dist(col, c) for c in solids) for col in original]
    remaining = []
    for a, b in candidates:
        col = mean(a, b)
        cost = penalty(a, b)
        remaining.append((a, b, [dist(orig, col) + cost for orig in original]))
    selected = []
    best = list(base)
    for _ in range(NPAIRS):
        score, chosen_index = max(
            ((sum(max(0, previous - current) for previous, current in zip(best, scores)), idx)
             for idx, (_, _, scores) in enumerate(remaining)),
            key=lambda x: (x[0], -x[1]),
        )
        if score <= 0:
            raise RuntimeError("No more useful checkerboard colors")
        a, b, costs = remaining.pop(chosen_index)
        selected.append((a, b))
        best = [min(p, c) for p, c in zip(best, costs)]
    # code 0..15 = solid; 16..31 = selected alternating 50/50 pair.
    rgb_codes = solids + [mean(a, b) for a, b in selected]
    penalties = [0] * 16 + [penalty(a, b) for a, b in selected]
    codes = [
        min(range(32), key=lambda j: dist(rgb, rgb_codes[j]) + penalties[j])
        for rgb in original
    ]
    score0 = sum(base)
    score1 = sum(best)
    report = {
        "mode": "r36-pixel4-32virtual",
        "samples": 76 * 44,
        "framebuffer_bytes": 76 * 44 // 2,
        "extra_bitplane_bytes": (76 * 44 + 7) // 8,
        "virtual_colors": 32,
        "solid_colors": 16,
        "checker_pairs": NPAIRS,
        "checker_doom_colors": sum(i >= 16 for i in codes),
        "estimated_weighted_error_reduction_pct": round(100 * (score0 - score1) / score0, 2),
        "pair_indices": selected,
        "lut_words_per_phase": 1024,
        "lut_rom_bytes": 2 * 1024 * 4,
        "cram_banks_during_gameplay": 1,
    }
    if report["checker_doom_colors"] < 20:
        raise RuntimeError(f"R36 ineffective checker quantization: {report}")
    return codes, selected, report


def row_word(code_left, code_right, pairs, odd):
    def half(code):
        if code < 16:
            return [code] * 4
        a, b = pairs[code - 16]
        return [a if (i + odd) % 2 == 0 else b for i in range(4)]
    word = 0
    for color in half(code_left) + half(code_right):
        word = (word << 4) | color
    return word


def make_row_tables(pairs):
    even, odd = [], []
    for index in range(1024):
        packed = index & 255
        high = index >> 8
        code_left = (packed >> 4) + (16 if high & 1 else 0)
        code_right = (packed & 15) + (16 if high & 2 else 0)
        even.append(row_word(code_left, code_right, pairs, 0))
        odd.append(row_word(code_left, code_right, pairs, 1))
        if high == 0:
            original = ((packed >> 4) * 0x11110000) | ((packed & 15) * 0x1111)
            assert even[-1] == odd[-1] == original
    assert len(even) == len(odd) == 1024
    return even, odd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    original = genpal.decode_subpal(genpal.load_playpal(), 0)
    solids = palette_rgb()
    color_map, pairs, report = choose_colors(original, solids)
    if __import__("os").environ.get("DOOM_R36C_HYBRID") == "1":
        palette_source = PALETTE.read_text(encoding="utf-8")
        found = re.search(r"r22_color\[256\]\s*=\s*\{([^}]*)\}", palette_source, re.S)
        if not found:
            raise RuntimeError("R36c missing solid-color plane quantizer")
        flat_lut = [int(v) for v in re.findall(r"\b\d+\b", found.group(1))]
        if len(flat_lut) != 256:
            raise RuntimeError("R36c expected 256 solid-color references")
        floor_slot, ceil_slot = flat_lut[107], flat_lut[106]
        floor_rgb, ceil_rgb = solids[floor_slot], solids[ceil_slot]
        if floor_slot != 1 or ceil_slot != 3 or tuple(floor_rgb) != (36,36,36) or tuple(ceil_rgb) != (73,73,73):
            raise RuntimeError(f"E1M1 mismatched cell reference: floor {floor_slot}:{floor_rgb}, ceiling {ceil_slot}:{ceil_rgb}")
        report["flat_reference"] = "R35d-cell-E1M1-sector0"
        report["e1m1_floor_doom_index"] = 107
        report["e1m1_floor_solid_rgb"] = list(floor_rgb)
        report["e1m1_ceiling_doom_index"] = 106
        report["e1m1_ceiling_solid_rgb"] = list(ceil_rgb)
        report["floor_ceiling_checkerboard"] = False
        report["wall_sprite_checkerboard"] = True
        report["leftmost_tile_column"] = "forced-black"
    even, odd = make_row_tables(pairs)
    def numbers(nums, per_line=8):
        return "\n".join(
            "    " + ", ".join(f"0x{n:08X}UL" for n in nums[i:i + per_line]) + ","
            for i in range(0, len(nums), per_line)
        )
    header = [
        "/* Autogenerated R36 pixel4 checker LUT. Do not edit. */",
        "#ifndef R36_PIXEL4_DITHER_H",
        "#define R36_PIXEL4_DITHER_H",
        "#include <stdint.h>",
        "static const uint8_t r36_color[256] = {",
        "    " + ", ".join(map(str, color_map[:128])) + ",",
        "    " + ", ".join(map(str, color_map[128:])) + "};",
        "static const uint32_t r36_row_even[1024] = {",
        numbers(even),
        "};",
        "static const uint32_t r36_row_odd[1024] = {",
        numbers(odd),
        "};",
        "#endif",
    ]
    OUTPUT.write_text("\n".join(header) + "\n", encoding="ascii")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("R36 pixel4 dither report:", json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
