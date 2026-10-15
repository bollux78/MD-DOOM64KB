#!/usr/bin/env python3
"""Inspect SGDK ELF memory headroom before attempting Mega Drive cache ROMs.

SGDK's standard md.ld locates RAM at E0FF0000..E1000000, and places
.data and .bss below the downward-growing stack and the dynamic heap.
A successful link does NOT establish stack/heap safety.
"""
import argparse
from pathlib import Path
import re
import subprocess

RAM_LOW = 0xE0FF0000
RAM_HIGH = 0xE1000000

def read_symbols(elf: Path, nm: str):
    cmd = [nm, "-n", str(elf)]
    data = subprocess.check_output(cmd, text=True)
    symbols = {}
    for line in data.splitlines():
        match = re.match(r"^([0-9a-fA-F]{6,16})\s+[a-zA-Z]\s+(\S+)\s*$", line)
        if match:
            symbols[match.group(2)] = int(match.group(1), 16)
    return symbols

def nearest_rom_symbol(symbols, addr):
    choices = [(v, name) for name, v in symbols.items()
               if v <= addr and 0 <= v < RAM_LOW]
    if not choices:
        return "unknown"
    offset, name = max(choices)
    return f"{name} + 0x{addr - offset:X} (symbol 0x{offset:06X})"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--elf", type=Path, default=Path("out/release/rom.out"))
    p.add_argument("--nm", default="m68k-elf-nm")
    p.add_argument("--variant", default="unknown")
    p.add_argument("--fault-pc", type=lambda v: int(v, 0), default=0x20FCA,
                   help="ROM address reported by BlastEm (Cache64 screenshot)")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if not args.elf.is_file():
        p.error(f"ELF not found: {args.elf}")

    symbols = read_symbols(args.elf, args.nm)
    bend = symbols.get("_bend")
    stack = symbols.get("__stack", RAM_HIGH)
    if bend is None:
        p.error("ELF has no _bend symbol; cannot estimate RAM usage")
    if not RAM_LOW <= bend <= RAM_HIGH or stack != RAM_HIGH:
        p.error(f"Unexpected linker RAM layout: _bend={bend:#x}, stack={stack:#x}")

    used = bend - RAM_LOW
    headroom = stack - bend
    # This is a static upper bound on heap + both stacks, not measured free heap.
    status = ("CRITICAL: <4KiB left for BOTH runtime stacks and heap" if headroom < 4096
              else "TIGHT: <8KiB left for runtime stacks and heap" if headroom < 8192
              else "Layout OK; still requires runtime validation")
    message = (
        f"Variant: {args.variant}\n"
        f"SGDK .data + .bss: {used} bytes ({used / 1024:.2f} KiB)\n"
        f"End of statics (_bend): 0x{bend:08X}\n"
        f"Top of RAM / stack:   0x{stack:08X}\n"
        f"Remaining for heap + stack(s): {headroom} bytes ({headroom / 1024:.2f} KiB)\n"
        f"Assessment: {status}\n"
        f"BlastEm fault instruction at 0x{args.fault_pc:06X}: "
        f"{nearest_rom_symbol(symbols, args.fault_pc)}\n"
        "Note: Address Error 0x010013 is an odd memory address;\n"
        "the instruction offset 0x020FCA is the place to investigate.\n"
        "The observed fault does not by itself prove stack collision.\n"
    )
    print(message)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(message, encoding="utf-8")

if __name__ == "__main__":
    main()
