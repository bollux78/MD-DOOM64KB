#!/usr/bin/env python3
"""R122: report/verify that the data the Z80 reads from cartridge ROM lies below $200000 (outside the SRAM overlay).

Usage: r122_z80_layout.py ELF [--require]
Z80-read objects: bgm_* (XGM2 music; size from <name>_size when present, else up to the next symbol), pcm_* (XGM2 PCM),
stop_xgm. Prints each range and the bytes at/above $200000; --require exits 1 if any byte is there.
"""
import os, subprocess, sys


def main():
    elf = sys.argv[1]; need = "--require" in sys.argv
    nm = os.environ.get("M68K_NM") or "nm"
    rows = []
    for l in subprocess.run([nm, "-S", "-n", elf], check=True, capture_output=True, text=True).stdout.splitlines():
        p = l.split()
        if len(p) == 4: rows.append((int(p[0], 16), int(p[1], 16), p[3]))
        elif len(p) == 3: rows.append((int(p[0], 16), None, p[2]))
    sizes = {n[:-5]: a for a, s, n in rows if n.endswith("_size") and s is None}
    rom = sorted((a, s, n) for a, s, n in rows if a < 0x400000 and not n.endswith("_size"))
    starts = [a for a, s, n in rom]
    out, bad = [], 0
    for i, (a, s, n) in enumerate(rom):
        base = n.split(".")[0]
        if not (base.startswith(("bgm_", "pcm_")) or base == "stop_xgm"): continue
        if s is None:
            s = sizes.get(base)
            if s is None: s = next((b for b in starts[i + 1:] if b > a), a) - a
        above = max(0, a + s - max(a, 0x200000))
        bad += above
        if base.startswith("bgm_") or above: out.append("%-28s %06x-%06x %7d B  above 2MB: %d" % (n, a, a + s, s, above))
    pcm = [(a, s, n) for a, s, n in rom if n.startswith("pcm_")]
    if pcm: out.append("pcm_* (%d objects) %06x-%06x" % (len(pcm), min(a for a, s, n in pcm), max(a + (s or 0) for a, s, n in pcm)))
    out.append("TOTAL Z80-read bytes at/above $200000: %d" % bad)
    print("\n".join(out))
    return 1 if (need and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
