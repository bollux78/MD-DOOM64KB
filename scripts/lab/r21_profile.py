#!/usr/bin/env python3
"""R21 N7b: turn the SRAM histogram of a DOOM_R21_PROF ROM into a per-function
profile.

Usage:
    python3 scripts/lab/r21_profile.py SAVE.sram ROM.elf [--top 40] [--nm m68k-elf-nm]

SAVE.sram  BlastEm writes cartridge SRAM when it quits (on Linux usually under
           ~/.local/share/blastem/<rom name>/save.sram); a flash cart writes
           it to its SD card. Odd-byte SRAM may be stored either compact
           (1 byte per SRAM byte) or interleaved with padding bytes; both are
           detected through the "R21P" magic.
ROM.elf    the ELF of the SAME build (out/release/rom.out / dist/*.elf).

Layout written by src/r21_prof.c (byte k of SRAM):
    0..3 "R21P", 4 version, 5 bucket shift, 6..9 base, 10..11 buckets,
    12..15 samples, 16..19 bad frames, 20..23 out of range, 24..27 frames,
    28 HInt line interval, 32.. buckets (big-endian u16, saturating).
Limits: samples are taken only in active display lines; time spent with
interrupts masked (VBlank ISR, the V3 DMA batch) collapses into one sample
on the next instruction, so DMA/ISR time is under-represented.
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys

MAGIC = b"R21P"


def load_sram(path):
    raw = open(path, "rb").read()
    # compact form
    if raw[:4] == MAGIC:
        return raw
    # interleaved forms: keep every other byte (odd or even lane)
    for lane in (1, 0):
        data = raw[lane::2]
        if data[:4] == MAGIC:
            return data
    idx = raw.find(MAGIC)
    if idx >= 0:
        return raw[idx:]
    raise SystemExit("R21P magic not found: not a DOOM_R21_PROF save, or the "
                     "emulator did not write SRAM (quit it normally).")


def find_nm(explicit):
    for cand in ([explicit] if explicit else []) + [os.environ.get("NM"),
                 "m68k-elf-nm", "m68k-linux-gnu-nm"]:
        if cand and shutil.which(cand):
            return cand
    raise SystemExit("no m68k nm found; pass --nm")


def symbols(elf, nm):
    out = subprocess.run([nm, "-n", "-S", elf], capture_output=True,
                         text=True, check=True).stdout
    syms = []
    for line in out.splitlines():
        p = line.split()
        if len(p) == 4 and p[2] in "tTwW":
            syms.append((int(p[0], 16), int(p[1], 16), p[3], p[2] in "TW"))
        elif len(p) == 3 and p[1] in "tTwW":
            syms.append((int(p[0], 16), 0, p[2], p[1] in "TW"))
    syms.sort()
    return syms  # linear scan in owner(): a few thousand symbols, fine


def owner(syms, addr):
    """Sized function containing addr; else nearest preceding named label."""
    best_sized, best_global = None, None
    for start, size, name, is_global in syms:
        if start > addr:
            break
        if name.startswith("."):
            continue
        if size and addr < start + size:
            best_sized = name
        if is_global and not size:
            best_global = name          # assembly routines (libgcc, SGDK .s)
    return best_sized or (best_global + "?" if best_global else "?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sram")
    ap.add_argument("elf")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--nm")
    ap.add_argument("--buckets", action="store_true", help="also print hottest 32-byte buckets")
    a = ap.parse_args()

    d = load_sram(a.sram)
    version, shift = d[4], d[5]
    base, = struct.unpack(">I", d[6:10])
    nb, = struct.unpack(">H", d[10:12])
    samples, bad, out, frames = struct.unpack(">IIII", d[12:28])
    lines = d[28]
    if version != 1:
        raise SystemExit("unknown layout version %d" % version)
    counts = [struct.unpack(">H", d[32 + 2 * b:34 + 2 * b])[0] for b in range(nb)]
    total = sum(counts)
    sat = sum(1 for c in counts if c == 0xFFFF)

    syms = symbols(a.elf, find_nm(a.nm))
    per = {}
    for b, c in enumerate(counts):
        if c:
            # attribute a bucket by its midpoint (buckets may straddle)
            name = owner(syms, base + (b << shift) + (1 << shift) // 2)
            per[name] = per.get(name, 0) + c

    print("samples %d (in histogram %d), bad frames %d, out of range %d, demo frames %d, every %d lines"
          % (samples, total, bad, out, frames, lines))
    if sat:
        print("WARNING: %d buckets saturated at 65535; raise R21_PROF_LINES" % sat)
    if bad:
        print("WARNING: bad frames > 0: stack layout differs from SGDK >= 1.80; profile not trustworthy")
    print("%-40s %9s %7s" % ("function", "samples", "%"))
    for name, c in sorted(per.items(), key=lambda kv: -kv[1])[:a.top]:
        print("%-40s %9d %6.2f%%" % (name[:40], c, 100.0 * c / max(total, 1)))
    if a.buckets:
        print("\nhottest buckets (32-byte granularity; a bucket may straddle two functions):")
        for b in sorted(range(nb), key=lambda b: -counts[b])[:20]:
            addr = base + (b << shift)
            mid = addr + (1 << shift) // 2
            print("  0x%06x %-34s %8d" % (addr, owner(syms, mid)[:34], counts[b]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
