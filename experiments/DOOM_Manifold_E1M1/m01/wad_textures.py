#!/usr/bin/env python3
"""Doom wall textures / flats / sky -> Manifold 16-colour resources (M04).

Reads PLAYPAL, PNAMES, TEXTURE1, patches and flats from the (shareware) IWAD,
composites the textures E1M1 uses, builds one 16-colour Mega Drive palette
for the 3D view (index 0 = transparent, used for sky), and emits:
  * textures.c  (Manifold format: 32 columns x 64 texels, u16 = 4 pixels)
  * colors.c light/distance tables recomputed for that palette
  * per-texture average colour index (upper/lower step colours, flats)
"""
from __future__ import annotations
import struct
from pathlib import Path

TEX_W, TEX_H = 32, 64


class Wad:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        n, off = struct.unpack_from("<II", self.data, 4)
        self.dir = []
        for i in range(n):
            pos, size, nm = struct.unpack_from("<II8s", self.data, off + 16 * i)
            self.dir.append((nm.rstrip(b"\0").decode("ascii", "replace").upper(), pos, size))

    def lump(self, name, after=0):
        for i in range(after, len(self.dir)):
            nm, pos, size = self.dir[i]
            if nm == name:
                return self.data[pos:pos + size]
        raise KeyError(name)

    def index(self, name):
        return [d[0] for d in self.dir].index(name)


def playpal(w):
    p = w.lump("PLAYPAL")[:768]
    return [tuple(p[i * 3:i * 3 + 3]) for i in range(256)]


def patch_image(data):
    wdt, hgt, _, _ = struct.unpack_from("<HHhh", data, 0)
    cols = struct.unpack_from(f"<{wdt}I", data, 8)
    img = [[None] * wdt for _ in range(hgt)]
    for x, off in enumerate(cols):
        while data[off] != 0xFF:
            top, length = data[off], data[off + 1]
            for k in range(length):
                y = top + k
                if 0 <= y < hgt:
                    img[y][x] = data[off + 3 + k]
            off += length + 4
    return wdt, hgt, img


def textures(w):
    pn = w.lump("PNAMES")
    n = struct.unpack_from("<I", pn, 0)[0]
    pnames = [pn[4 + 8 * i:12 + 8 * i].rstrip(b"\0").decode().upper() for i in range(n)]
    out = {}
    for lumpname in ("TEXTURE1", "TEXTURE2"):
        try:
            t = w.lump(lumpname)
        except KeyError:
            continue
        cnt = struct.unpack_from("<I", t, 0)[0]
        offs = struct.unpack_from(f"<{cnt}I", t, 4)
        for o in offs:
            nm, _, wdt, hgt, _, npatch = struct.unpack_from("<8sIHHIH", t, o)
            nm = nm.rstrip(b"\0").decode().upper()
            patches = []
            for k in range(npatch):
                ox, oy, pi, _, _ = struct.unpack_from("<hhHHH", t, o + 22 + 10 * k)
                patches.append((ox, oy, pnames[pi]))
            out[nm] = (wdt, hgt, patches)
    return out


def compose(w, texdefs, name, cache={}):
    wdt, hgt, patches = texdefs[name]
    img = [[0] * wdt for _ in range(hgt)]
    for ox, oy, pname in patches:
        if pname not in cache:
            try:
                cache[pname] = patch_image(w.lump(pname))
            except KeyError:
                continue
        pw, ph, pim = cache[pname]
        for y in range(ph):
            for x in range(pw):
                v = pim[y][x]
                if v is not None and 0 <= x + ox < wdt and 0 <= y + oy < hgt:
                    img[y + oy][x + ox] = v
    return wdt, hgt, img


def flat(w, name):
    start = w.index("F_START")
    return w.lump(name, start)          # 64x64 indexed


# ---------------- palette ----------------
def md(c):
    """Quantise RGB to Mega Drive 3-bit channels (returned as 0-255 RGB)."""
    return tuple(min(7, round(v / 255 * 7)) * 255 // 7 for v in c)


def vdp(c):
    r, g, b = (min(7, round(v / 255 * 7)) for v in c)
    return (b << 9) | (g << 5) | (r << 1)


def dist2(a, b):
    # weighted perceptual-ish distance
    return 2 * (a[0] - b[0]) ** 2 + 4 * (a[1] - b[1]) ** 2 + 3 * (a[2] - b[2]) ** 2


def kmeans(samples, k, iters=20):
    # deterministic seeding: spread over luminance
    samples = sorted(samples, key=lambda c: c[0] * 3 + c[1] * 6 + c[2])
    cents = [samples[int(i * (len(samples) - 1) / (k - 1))] for i in range(k)]
    for _ in range(iters):
        acc = [[0, 0, 0, 0] for _ in cents]
        for s in samples:
            j = min(range(k), key=lambda i: dist2(s, cents[i]))
            a = acc[j]; a[0] += s[0]; a[1] += s[1]; a[2] += s[2]; a[3] += 1
        cents = [(a[0] / a[3], a[1] / a[3], a[2] / a[3]) if a[3] else cents[i] for i, a in enumerate(acc)]
    return cents


def build_palette(rgb_samples):
    """Greedy facility-location over the 512 Mega Drive colours: always 15
    distinct entries (k-means centroids collapse after 3-bit quantisation)."""
    from collections import Counter
    hist = Counter()
    for i, c in enumerate(rgb_samples):
        hist[md(c)] += 1
        if i % 2 == 0:
            hist[md(tuple(v * 0.5 for v in c))] += 1     # room for shading
    bins = list(hist.items())
    cand = sorted({md((r * 255 / 7, g * 255 / 7, b * 255 / 7)) for r in range(8) for g in range(8) for b in range(8)})
    cand = [c for c in cand if c != (0, 0, 0)]
    best = [min(dist2(c, (0, 0, 0)), 10**9) for c, _ in bins]
    chosen = []
    for _ in range(15):
        top = None
        for k in cand:
            if k in chosen:
                continue
            gain = 0
            for j, (c, n) in enumerate(bins):
                d = dist2(c, k)
                if d < best[j]:
                    gain += (best[j] - d) * n
            if top is None or gain > top[0]:
                top = (gain, k)
        chosen.append(top[1])
        best = [min(best[j], dist2(c, top[1])) for j, (c, _) in enumerate(bins)]
    return [(0, 0, 0)] + sorted(chosen, key=lambda c: c[0] * 3 + c[1] * 6 + c[2])


def nearest(pal, c, lo=1):
    return min(range(lo, len(pal)), key=lambda i: dist2(c, pal[i]))


def nearest_pair(pal, c, lo=1):
    """Best 50/50 dither pair (p, q) for colour c."""
    best = None
    cand = sorted(range(lo, len(pal)), key=lambda i: dist2(c, pal[i]))[:6]
    for p in cand:
        for q in cand:
            m = tuple((pal[p][k] + pal[q][k]) / 2 for k in range(3))
            d = dist2(c, m) + (0 if p == q else 40)   # slight bias to solid
            if best is None or d < best[0]:
                best = (d, p, q)
    return best[1], best[2]


# ---------------- emitters ----------------
def scale_rgb(c, f):
    return tuple(min(255, v * f) for v in c)


def texture_words(pal, rgb_img, wdt, hgt, factor):
    """32x64 column-major u16 words, each = 4 screen pixels (dither pair)."""
    words = []
    for u in range(TEX_W):
        x0, x1 = u * wdt / TEX_W, (u + 1) * wdt / TEX_W
        for v in range(TEX_H):
            y0, y1 = v * hgt / TEX_H, (v + 1) * hgt / TEX_H
            acc = [0, 0, 0]; n = 0
            for yy in range(int(y0), max(int(y0) + 1, int(y1))):
                for xx in range(int(x0), max(int(x0) + 1, int(x1))):
                    c = rgb_img[yy][xx]
                    acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]; n += 1
            c = scale_rgb((acc[0] / n, acc[1] / n, acc[2] / n), factor)
            p, q = nearest_pair(pal, c)
            words.append((p << 12) | (q << 8) | (p << 4) | q)
    return words


LIGHT_FACTORS = {  # (table, light level) -> brightness factor
    ("far", -2): 0.30, ("far", -1): 0.42, ("far", 0): 0.58, ("far", 1): 0.80, ("far", 2): 1.0,
    ("near", -2): 0.40, ("near", -1): 0.60, ("near", 0): 1.0, ("near", 1): 1.15, ("near", 2): 1.3,
}


def colors_tables(pal):
    def table(dither):
        rows = []
        for dist in ("far", "near"):
            for lv in (-2, -1, 0, 1, 2):
                f = LIGHT_FACTORS[(dist, lv)]
                vals = ["0"]
                for i in range(1, 16):
                    c = scale_rgb(pal[i], f)
                    if dither:
                        p, q = nearest_pair(pal, c)
                    else:
                        p = q = nearest(pal, c)
                    vals.append(f"DPIX({p},{q})")
                rows.append("   " + ", ".join(vals) + ",")
        return "\n".join(rows)
    return table(True), table(False)


def rgb_of(pal256, img):
    return [[pal256[v] for v in row] for row in img]


def average(rgb_img):
    n = 0; acc = [0, 0, 0]
    for row in rgb_img:
        for c in row:
            acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]; n += 1
    return (acc[0] / n, acc[1] / n, acc[2] / n)


def build_resources(wad_path, tex_names, flat_names, sky_name="SKY1"):
    """Return dict with palette, per-texture data and colour indices."""
    w = Wad(wad_path)
    pal256 = playpal(w)
    defs = textures(w)
    texrgb = {}
    for nm in tex_names:
        wdt, hgt, img = compose(w, defs, nm)
        texrgb[nm] = (wdt, hgt, rgb_of(pal256, img))
    flatrgb = {}
    for nm in flat_names:
        raw = flat(w, nm)
        flatrgb[nm] = [[pal256[raw[y * 64 + x]] for x in range(64)] for y in range(64)]
    sky = None
    if sky_name in defs:
        wdt, hgt, img = compose(w, defs, sky_name)
        sky = (wdt, hgt, rgb_of(pal256, img))
    # palette samples: subsampled texels of every texture + flats + sky
    samples = []
    for wdt, hgt, img in texrgb.values():
        for y in range(0, hgt, 4):
            for x in range(0, wdt, 4):
                samples.append(img[y][x])
    for img in flatrgb.values():
        for y in range(0, 64, 8):
            for x in range(0, 64, 8):
                samples.append(img[y][x])
    pal = build_palette(samples)
    return {"pal": pal, "tex": texrgb, "flats": flatrgb, "sky": sky}


def emit_textures_c(res, names):
    pal = res["pal"]
    out = ['#include "manifold_mute_klog.h"', "#include <genesis.h>",
           '#include "real_timer.h"', '#include "texture.h"', "",
           "/* GENERATED from Doom shareware textures (E1M1) for this experiment */"]
    table = ["(lit_texture*)(0xBEEFF00F),"]
    for i, nm in enumerate(names):
        wdt, hgt, img = res["tex"][nm]
        for variant, f in (("mid", 1.0), ("dark", 0.55)):
            words = texture_words(pal, img, wdt, hgt, f)
            out.append(f"const u16 doomtex_{i}_{variant}[{TEX_W}*{TEX_H}] = {{")
            for k in range(0, len(words), TEX_H):
                out.append("  " + ", ".join(f"0x{v:04x}" for v in words[k:k + TEX_H]) + ",")
            out.append("};")
        for lv, (d, m, l) in (("dark", ("dark", "dark", "mid")), ("mid", ("dark", "dark", "mid")),
                              ("light", ("mid", "mid", "mid"))):
            out.append(f"const lit_texture doomlit_{i}_{lv} = {{ .dark = doomtex_{i}_{d}, "
                       f".mid = doomtex_{i}_{m}, .light = doomtex_{i}_{l} }};")
        table += [f"&doomlit_{i}_dark,", f"&doomlit_{i}_mid,", f"&doomlit_{i}_mid,",
                  f"&doomlit_{i}_mid,", f"&doomlit_{i}_light,", "NULL,", "NULL,", "NULL,"]
    while len(table) < 1 + 64 * 8:
        table.append("NULL,")
    out.append("const lit_texture* const textures[1+ 64*8] = {")
    out += ["  " + t for t in table]
    out.append("};")
    return "\n".join(out) + "\n"


def sky_tiles(res, band_rows=6, band_cols=16, max_tiles=96):
    """SKY1 -> deduplicated 4bpp tiles for a BG_B band (3D palette)."""
    pal = res["pal"]
    wdt, hgt, img = res["sky"]
    while True:
        W, H = band_cols * 8, band_rows * 8
        px = [[None] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                sx0, sx1 = int(x * wdt / W), max(int(x * wdt / W) + 1, int((x + 1) * wdt / W))
                sy0, sy1 = int(y * hgt / H), max(int(y * hgt / H) + 1, int((y + 1) * hgt / H))
                acc = [0, 0, 0]; n = 0
                for yy in range(sy0, sy1):
                    for xx in range(sx0, sx1):
                        c = img[yy][xx]; acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]; n += 1
                px[y][x] = nearest(pal, (acc[0] / n, acc[1] / n, acc[2] / n))
        top = nearest(pal, average([img[0]]))
        bot = nearest(pal, average([img[hgt - 1]]))
        tiles, index, tmap = [], {}, []
        def add(t):
            if t not in index:
                index[t] = len(tiles); tiles.append(t)
            return index[t]
        add(tuple(sum(top << (28 - 4 * k) for k in range(8)) for _ in range(8)))
        add(tuple(sum(bot << (28 - 4 * k) for k in range(8)) for _ in range(8)))
        for ty in range(band_rows):
            row = []
            for tx in range(band_cols):
                t = tuple(sum(px[ty * 8 + r][tx * 8 + k] << (28 - 4 * k) for k in range(8)) for r in range(8))
                row.append(add(t))
            tmap.append(row)
        if len(tiles) <= max_tiles or band_rows <= 2:
            return {"tiles": tiles, "map": tmap, "rows": band_rows, "cols": band_cols}
        band_rows -= 1
