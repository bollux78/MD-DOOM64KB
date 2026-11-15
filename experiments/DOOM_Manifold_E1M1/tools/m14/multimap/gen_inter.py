#!/usr/bin/env python3
"""Intermission screen: 320x224 image (<=32 colours) -> blob placed at ROM 0x2F0000 (see compose.py).
Blob (big endian): pal[64] u16 | attr[1120] u16 | tiles[1120*8] u32.  Same two-sub-palette scheme as gen_assets.py."""
import struct, sys, random, collections
from PIL import Image
src = Image.open("/home/claude/md-doom64kb/assets/art/doom-intermission-md-30col.png").convert("RGB")
W, H = 320, 224
pix_rgb = list(src.getdata())
uniq = sorted(set(pix_rgb), key=lambda c: -pix_rgb.count(c))
assert len(uniq) <= 32, len(uniq)
rgb = uniq + [uniq[0]] * (32 - len(uniq))
idx = {c: i for i, c in enumerate(uniq)}
pix = [idx[c] for c in pix_rgb]
lv = lambda v: min(7, round(v / 36.4))
md = lambda c: (lv(c[2]) << 9) | (lv(c[1]) << 5) | (lv(c[0]) << 1)
X = collections.Counter(pix).most_common(1)[0][0]
tiles_px = [[pix[(ty*8+y)*W + tx*8 + x] for y in range(8) for x in range(8)] for ty in range(H//8) for tx in range(W//8)]
def d2(a, b): return sum((x-y)**2 for x, y in zip(rgb[a], rgb[b]))
random.seed(1)
NP = 4
assign = [random.randint(0, NP-1) for _ in tiles_px]
pals = [list(range(16))] * NP
def tile_cost(t, pal): return sum(min(d2(c, p) for p in pal) for c in t)
for it in range(14):
    for k in range(NP):
        cnt = {}
        for t, a in zip(tiles_px, assign):
            if a == k:
                for c in t: cnt[c] = cnt.get(c, 0) + 1
        chosen = [X]; cand = list(cnt)
        while len(chosen) < min(16, len(cand) + 1):
            best = None
            for c in cand:
                if c in chosen: continue
                tr = chosen + [c]
                e = sum(n * min(d2(x, p) for p in tr) for x, n in cnt.items())
                if best is None or e < best[0]: best = (e, c)
            chosen.append(best[1])
        while len(chosen) < 16: chosen.append(chosen[0])
        pals[k] = chosen
    na = [min(range(NP), key=lambda k: tile_cost(t, pals[k])) for t in tiles_px]
    if na == assign: break
    assign = na
err = sum(min(tile_cost(t, pals[k]) for k in range(NP)) for t in tiles_px)
print("sq error", err)
cram = [md(rgb[c]) for k in range(NP) for c in pals[k]]
blob = bytearray()
for c in cram: blob += struct.pack(">H", c)
for a in assign: blob += struct.pack(">H", a << 13)
pv = Image.new("RGB", (W, H)); pp = pv.load()
for n, (t, a) in enumerate(zip(tiles_px, assign)):
    tx, ty = n % 40, n // 40
    for y in range(8):
        row = 0
        for x in range(8):
            i = min(range(16), key=lambda i: d2(t[y*8+x], pals[a][i]))
            row = (row << 4) | i
            pp[tx*8+x, ty*8+y] = rgb[pals[a][i]]
        blob += struct.pack(">I", row)
open("inter.bin", "wb").write(blob); pv.save("/tmp/m14x/inter_q16.png")
print("blob", len(blob))
