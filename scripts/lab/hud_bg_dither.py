#!/usr/bin/env python3
"""Background-only dithering study for the recreated status bar. Source: original STBAR + STARMS from the user's IWAD, squeezed
320 -> 256 px (area average), then reduced to a k-colour Mega Drive palette (3 bits/channel) with different dithers.
Output: one indexed PNG, 256x32 strips separated by 2 px, in this fixed order (a legend is added by the viewer):
  0 reference (squeezed, 64 colours)   1 nearest k=12   2 Floyd-Steinberg k=12   3 Bayer 4x4 k=12   4 Bayer 8x8 k=12
  5 nearest k=8   6 Floyd-Steinberg k=8   7 Bayer 4x4 k=8   8 Bayer 8x8 k=8
Optionally a base64 dump for CI annotations. Reads the IWAD only; nothing derived is committed."""
import argparse, base64, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gen_hud_wad as g
from hud_images import indexed_png
from hud_bg_images import stbar

W, H = 256, 32
DIST = lambda a, b: 2 * (a[0] - b[0]) ** 2 + 4 * (a[1] - b[1]) ** 2 + 3 * (a[2] - b[2]) ** 2


def nearest(pal, c):
    return min(pal, key=lambda p: DIST(p, c))


def clamp(v):
    return 0 if v < 0 else 255 if v > 255 else int(v)


def bayer(n):
    m = [[0]]
    while len(m) < n:
        k = len(m)
        m = [[4 * m[y % k][x % k] + [[0, 2], [3, 1]][y // k][x // k] for x in range(2 * k)] for y in range(2 * k)]
    return m


def dither_none(img, pal):
    return [[nearest(pal, px) for px in r] for r in img]


def dither_fs(img, pal):
    h, w = len(img), len(img[0])
    buf = [[list(map(float, px)) for px in r] for r in img]
    out = [[None] * w for _ in range(h)]
    for y in range(h):
        xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
        d = 1 if y % 2 == 0 else -1
        for x in xs:
            old = tuple(clamp(v) for v in buf[y][x])
            new = nearest(pal, old)
            out[y][x] = new
            err = [old[i] - new[i] for i in range(3)]
            for dx, dy, f in ((d, 0, 7 / 16), (-d, 1, 3 / 16), (0, 1, 5 / 16), (d, 1, 1 / 16)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h:
                    for i in range(3):
                        buf[yy][xx][i] += err[i] * f
    return out


def dither_bayer(img, pal, n, spread):
    m = bayer(n)
    area = n * n
    out = []
    for y, r in enumerate(img):
        row = []
        for x, px in enumerate(r):
            t = ((m[y % n][x % n] + 0.5) / area - 0.5) * spread
            row.append(nearest(pal, tuple(clamp(c + t) for c in px)))
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wad", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--b64")
    a = ap.parse_args()
    lumps = g.read_iwad(open(a.wad, "rb").read())
    full = stbar(lumps, True)
    ref = g.box_resample([[px for px in r] for r in full], W, H, (0, 0, 0))
    weights = {}
    for r in ref:
        for px in r:
            weights[px] = weights.get(px, 0) + 1
    ref64 = dither_none(ref, g.quantise_palette(weights, k=64))      # reference strip: 64 colours (keeps the PNG indexed)
    strips = [ref64]
    for k in (12, 8):
        pal = g.quantise_palette(weights, k=k)
        spread = 56 if k == 12 else 80
        strips += [dither_none(ref, pal), dither_fs(ref, pal), dither_bayer(ref, pal, 4, spread), dither_bayer(ref, pal, 8, spread)]
    img = []
    for s in strips:
        img += s + [[(40, 40, 40)] * W] * 2
    data = indexed_png(a.out, img)
    print("dither study", len(data), "bytes;", len(strips), "strips")
    if a.b64:
        open(a.b64, "w").write("ORIG " + base64.b64encode(data).decode() + "\n")


if __name__ == "__main__":
    main()
