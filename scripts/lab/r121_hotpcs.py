#!/usr/bin/env python3
"""R121: annotate the disassembly of the hottest functions with PC sample counts (no demo data, code only).

Usage: r121_hotpcs.py --elf ELF --out OUT.txt [--top 8] [--tic-min A --tic-max B] samples.tsv [samples.tsv ...]
samples.tsv rows: tic, leveltime, pc(hex), caller(hex)[, vblank]. Uses $OBJDUMP (m68k-elf-objdump).
For each of the --top functions by samples: total, then every instruction with >= 1 sample shown with
its count and +-2 lines of context; also the caller-hint split for helper functions.
"""
import argparse, bisect, collections, os, subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=8); ap.add_argument("--tic-min", type=int, default=0); ap.add_argument("--tic-max", type=int, default=1 << 30)
    ap.add_argument("samples", nargs="+")
    a = ap.parse_args()
    od = os.environ.get("OBJDUMP") or os.path.expanduser("~/mars/m68k-elf/bin/m68k-elf-objdump")
    text = subprocess.run([od, "-d", a.elf], check=True, capture_output=True, text=True).stdout
    funcs, lines, cur = [], {}, None
    for l in text.splitlines():
        if l.endswith(">:") and " <" in l:
            addr, name = l.split(" <", 1); cur = name[:-2]; funcs.append((int(addr, 16), cur)); lines[cur] = []
        elif cur and ":\t" in l:
            try: lines[cur].append((int(l.split(":", 1)[0], 16), l.strip()))
            except ValueError: pass
    funcs.sort(); starts = [f[0] for f in funcs]
    fn = lambda pc: funcs[bisect.bisect_right(starts, pc) - 1][1] if pc >= starts[0] else "?"
    pcs, callers, n = collections.Counter(), collections.Counter(), 0
    for p in a.samples:
        for l in open(p):
            c = l.split("\t")
            if len(c) < 4 or not (a.tic_min <= int(c[0]) <= a.tic_max): continue
            pc, ret = int(c[2], 16), int(c[3], 16); pcs[pc] += 1; n += 1
            if fn(pc).startswith(("__mulsi3", "__udivsi3", "__divsi3", "R23_Map", "R89_Visit", "L4", "memcpy")): callers[(fn(pc), fn(ret) if ret else "?")] += 1
    byf = collections.Counter()
    for pc, c in pcs.items(): byf[fn(pc)] += c
    out = ["R121 hot PCs: %d samples, tics %d..%d" % (n, a.tic_min, min(a.tic_max, 1 << 30)), ""]
    out += ["%6.2f%%  %6d  %s" % (100 * c / max(n, 1), c, f) for f, c in byf.most_common(30)]
    out += ["", "Helper callers (caller hint):"] + ["%6d  %s <- %s" % (c, f, r) for (f, r), c in callers.most_common(25)]
    for f, c in byf.most_common(a.top):
        out += ["", "=" * 100, "%s: %d samples (%.2f%%)" % (f, c, 100 * c / max(n, 1)), "=" * 100]
        L = lines.get(f, []); hot = {i for i, (ad, _) in enumerate(L) if pcs.get(ad)}
        show = sorted({j for i in hot for j in range(i - 2, i + 3) if 0 <= j < len(L)})
        prev = None
        for j in show:
            if prev is not None and j != prev + 1: out.append("        ...")
            ad, s = L[j]; out.append("%6s  %s" % (pcs.get(ad, "") or "", s)); prev = j
    open(a.out, "w").write("\n".join(out) + "\n")
    print("\n".join(out[:40]))


if __name__ == "__main__":
    main()
