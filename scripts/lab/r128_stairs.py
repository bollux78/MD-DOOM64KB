#!/usr/bin/env python3
"""R128 stairs: merge pairs of small steps in the converted WAD so the riser between them disappears.

Behaviour change accepted by the user (2026-11-04): maps may differ slightly if they stay recognisable.
For every two-sided, special-free line between two sectors that are identical except for a small floor
step (same ceiling height, floor colour, ceiling colour, light; no special, no tag; not next to any
special line; no middle texture on the line), the lower floor is raised to the upper one. R_RecalcLineFlags
then marks the riser RF_IGNORE (identical sectors) and the renderer skips it. Greedy pairing: a sector is
changed at most once and its neighbours are locked for this pass. Steps <= 8: the lower floor rises to the
upper one. Steps of 9..16 (E1M1's stairs are 16): both floors go to the middle, so the risers on either side
become <= 24 (Doom's step limit). No change may create a new step-up above 24; headroom stays >= 56.
Usage: r128_stairs.py WAD [--maps 1,2,...] [--max-step 8]
"""
import argparse, json, pathlib, struct, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from convert_r24_episode import read_wad, write_wad

SEC = struct.Struct('>hhhhBbh')                   # floor, ceil, floor colour, ceil colour, light, special, tag
SIDE = struct.Struct('>hBbbbB')                   # x, y, top, bottom, mid, sector
LINE = struct.Struct('>hhhhHhhHHhhhhhBbb')        # 31 bytes (+1 pad after r89_align_maps)


def process(lumps, i0, max_step):
    idx = {}
    j = i0 + 1
    while j < len(lumps) and not (lumps[j][0].startswith('E1M') and len(lumps[j][0]) == 4):
        idx.setdefault(lumps[j][0], j); j += 1
    sec = [list(SEC.unpack_from(lumps[idx['SECTORS']][1], o)) for o in range(0, len(lumps[idx['SECTORS']][1]), SEC.size)]
    sides = [SIDE.unpack_from(lumps[idx['SIDEDEFS']][1], o) for o in range(0, len(lumps[idx['SIDEDEFS']][1]), SIDE.size)]
    ld = lumps[idx['LINEDEFS']][1]; rec = 32 if len(ld) % 32 == 0 and len(ld) % 31 else 31
    lines = [LINE.unpack_from(ld, o) for o in range(0, len(ld), rec)]
    near_special = set()
    for l in lines:
        if l[16] or l[13]:
            for sd in (l[7], l[8]):
                if sd != 65535: near_special.add(sides[sd][5])
    nb = {}
    for l in lines:
        if l[8] == 65535: continue
        x, y = sides[l[7]][5], sides[l[8]][5]
        if x != y: nb.setdefault(x, set()).add(y); nb.setdefault(y, set()).add(x)
    def ok(s, h, other):
        # no new step-up above 24 between s (new floor h) and any neighbour; headroom >= 56
        if sec[s][1] - h < 56: return False
        for n in nb.get(s, ()):
            if n == other: continue
            old, new = abs(sec[s][0] - sec[n][0]), abs(h - sec[n][0])
            if new > 24 and old <= 24: return False
        return True
    locked, merged = set(), 0
    for l in lines:
        if l[8] == 65535 or l[16] or l[13]: continue
        a, b = sides[l[7]][5], sides[l[8]][5]
        if a == b or sides[l[7]][4] or sides[l[8]][4]: continue
        A, B = sec[a], sec[b]
        if any(x[5] or x[6] for x in (A, B)) or a in near_special or b in near_special: continue
        if any(sec[n][5] or sec[n][6] or n in near_special for n in nb.get(a, set()) | nb.get(b, set())): continue  # lifts/doors use surrounding floors
        if (A[1], A[2], A[3], A[4]) != (B[1], B[2], B[3], B[4]): continue
        d = abs(B[0] - A[0])
        if d == 0 or d > max_step or a in locked or b in locked: continue
        lo, hi = (a, b) if B[0] > A[0] else (b, a)
        # d <= 8: raise the lower step; 8 < d <= 16: both to the middle (neighbour risers become <= 24).
        h = sec[hi][0] if d <= 8 else sec[lo][0] + d // 2
        if not (ok(lo, h, hi) and ok(hi, h, lo)): continue
        sec[lo][0] = h; sec[hi][0] = h; merged += 1
        locked |= {lo, hi} | nb.get(lo, set()) | nb.get(hi, set())
    lumps[idx['SECTORS']] = ('SECTORS', b''.join(SEC.pack(*s) for s in sec))
    return merged


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('wad'); ap.add_argument('--maps', default='1,2,3,4,5,6,7,8,9')
    ap.add_argument('--max-step', type=int, default=16)
    a = ap.parse_args(); p = pathlib.Path(a.wad)
    lumps = read_wad(p.read_bytes(), True); rep = {}
    for m in a.maps.split(','):
        i0 = next(i for i, (n, _) in enumerate(lumps) if n == 'E1M' + m)
        rep['E1M' + m] = process(lumps, i0, a.max_step)
    p.write_bytes(write_wad(lumps)); print('R128 stairs merged steps:', json.dumps(rep))


if __name__ == '__main__':
    main()
