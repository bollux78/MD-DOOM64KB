#!/usr/bin/env python3
"""Generate bit-exact reciprocal scale LUT for the 68000 R12 experiment.

Every entry is floor(0x01ffffff / scale), equal to the R11 DIVU.W
result. Only scales >=512 fit in 16 bits. Table stays in ROM (.rodata).
"""
import argparse
from pathlib import Path

VALID = (4095, 16383, 65535)
MIN = 512

def value(scale: int) -> int:
    return 0x01FFFFFF // scale

def generate(limit: int, path: Path) -> None:
    assert limit in VALID
    lines = [
        "/* GENERATED: scripts/lab/gen_r12_recip_lut.py. Do not edit. */",
        "#ifndef R12_RECIP_LUT_H",
        "#define R12_RECIP_LUT_H",
        f"#define R12_RECIP_MAX {limit}u",
        f"static const uint16_t r12_recip_table[{limit - MIN + 1}] = {{",
    ]
    for start in range(MIN, limit + 1, 12):
        vals = [value(x) for x in range(start, min(start + 12, limit + 1))]
        assert all(0 <= v <= 0xFFFF for v in vals)
        lines.append("    " + ", ".join(f"{v}u" for v in vals) + ",")
    lines += ["};", "#endif", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="ascii")
    print(f"R12: generated {limit - MIN + 1} x 2 = {2 * (limit - MIN + 1)} ROM bytes, scale 512..{limit}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--max-scale", type=int, required=True, choices=VALID)
    p.add_argument("--output", type=Path, default=Path("src/r12_recip_lut.h"))
    args = p.parse_args()
    generate(args.max_scale, args.output)
