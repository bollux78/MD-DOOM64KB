#!/usr/bin/env python3
"""Rank RAM-resident ELF symbols by allocated size (SGDK / m68k-elf-nm).

This is a *static* view: linker padding, anonymous sections, actual stack depth
and dynamic allocations are not accounted for. It does not prove runtime safety.
"""
import argparse
from pathlib import Path
import re
import subprocess

RAM_START = 0xE0FF0000
RAM_END = 0xE1000000
SYMBOL_LINE = re.compile(r"^([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([A-Za-z])\s+(.+)$")


def ram_symbols(nm_output):
    symbols = []
    for line in nm_output.splitlines():
        match = SYMBOL_LINE.match(line.strip())
        if not match:
            continue
        address = int(match.group(1), 16)
        size = int(match.group(2), 16)
        kind = match.group(3)
        name = match.group(4)
        if RAM_START <= address < RAM_END and size > 0 and kind.lower() in "bdscg":
            symbols.append((size, address, kind, name))
    return sorted(symbols, reverse=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--elf", type=Path, required=True)
    ap.add_argument("--nm", default="m68k-elf-nm")
    ap.add_argument("--variant", default="unknown")
    ap.add_argument("--top", type=int, default=35)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if not args.elf.is_file():
        ap.error(f"ELF not found: {args.elf}")
    # -S provides sizes; -a includes local symbols (e.g. static heap array).
    result = subprocess.run([args.nm, "-a", "-S", str(args.elf)],
                            text=True, capture_output=True, check=True)
    symbols = ram_symbols(result.stdout)
    if not symbols:
        ap.error("No sized RAM symbols found; check nm version and ELF format")
    lines = [
        f"Variant: {args.variant}",
        f"Sized RAM symbols found: {len(symbols)}",
        "Largest symbols (size is hex-decoded, output in decimal bytes):",
        "BYTES     ADDRESS     TYPE NAME",
    ]
    for size, addr, kind, name in symbols[:args.top]:
        lines.append(f"{size:9d}  0x{addr:08X}  {kind:>3}  {name}")
    lines.extend([
        "",
        "WARNING: sums of sized symbols do not equal total .data + .bss.",
        "Unattributed sections, alignment and SGDK libraries may contribute.",
        "Use ram_usage.py for exact static headroom and a running ROM for zone peak.",
    ])
    message = "\n".join(lines) + "\n"
    print(message)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(message, encoding="utf-8")


if __name__ == "__main__":
    main()
