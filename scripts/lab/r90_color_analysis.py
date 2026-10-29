#!/usr/bin/env python3
"""R90 colour analysis (offline, no ROM): how close can per-map palettes bring the view to Doom's colours?

Inputs: the pinned shareware IWAD (little-endian, original 8-bit PLAYPAL) and the R89 colour tables
(r59_color_tables.h from the R89 build artifact).  Nothing here changes a ROM.

1. Per-map screen proxy (E1M1..E1M9): what Doom colours a player sees, after COLORMAP lighting.
   walls  : every visible sidedef texture, weight = linedef length x visible height, texels of the
            composited texture, light = sector light spread over the distance-shading levels.
   flats  : the MD draws a solid colour per flat (jWadUtil picnum = representative palette index);
            weight = sector area; light = sector light.
   sprites: things of the map (frame A), fixed share of the screen.
   Shares: walls 0.50, flats 0.40, sprites 0.10 (screen-coverage proxy, documented, not measured).
2. Display model of the MD view: a code n of plane P shows the M50 mix of PAL_P[pairs[n][0]] and
   PAL_P[pairs[n][1]]; even and odd sample columns are averaged by the eye (linear light).
   DAC models: LIN (k*255/7, what the generators assume) and HW (measured Mega Drive levels).
3. Candidates, all evaluated with the same metric (CIELAB dE76 vs the original 8-bit PLAYPAL):
   R89 modes 0..3 as shipped (comp LUTs per light level, flat LUTs for flats);
   GEN-global  : R52-style objective on the episode histogram, candidates = PLAYPAL words (as today), LIN;
   GEN-map     : same objective on each map's histogram;
   GEN-map-HW  : per map, all 511 MD colours as candidates, HW DAC in the optimisation;
   generated sets get R53-style M50 companions so they are comparable with the shipped modes.
Outputs: report.json and REPORT.md (+ swatches PNG if Pillow is present).
"""
import argparse, json, math, re, struct, sys, time
from pathlib import Path
import numpy as np

DAC = {"LIN": np.array([0, 36.43, 72.86, 109.29, 145.71, 182.14, 218.57, 255.0]),
       "HW": np.array([0, 52, 87, 116, 144, 172, 206, 255], float)}
SHARE = {"walls": 0.50, "flats": 0.40, "sprites": 0.10}
MAPS = ["E1M%d" % i for i in range(1, 10)]
# doomednum -> sprite prefix (E1 shareware things that are visible and common)
THING_SPR = {3004: "POSS", 9: "SPOS", 3001: "TROO", 3002: "SARG", 58: "SARG", 3003: "BOSS", 2035: "BAR1",
             2014: "BON1", 2015: "BON2", 2011: "STIM", 2012: "MEDI", 2008: "SHEL", 2007: "CLIP", 2048: "AMMO",
             2049: "SBOX", 2001: "SHOT", 2002: "MGUN", 2003: "LAUN", 2004: "PLAS", 2018: "ARM1", 2019: "ARM2",
             5: "BKEY", 6: "YKEY", 13: "RKEY", 2028: "COLU", 34: "CAND", 35: "CBRA", 46: "TRED", 48: "ELEC",
             2025: "SUIT", 2024: "PINS", 2022: "PINV", 2026: "PMAP", 2045: "PVIS", 2013: "SOUL", 10: "PLAY",
             12: "PLAY", 15: "PLAY", 24: "POL5", 2046: "BROK", 17: "CELP", 2047: "CELL"}

# ------------------------------------------------------------------ colour maths
_M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
_WHITE = np.array([0.95047, 1.0, 1.08883])
def srgb2lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def lin2srgb(l):
    l = np.clip(l, 0.0, 1.0)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * l ** (1 / 2.4) - 0.055) * 255.0
def lab_from_lin(lin):
    xyz = (lin @ _M.T) / _WHITE
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def to_lab(c8):
    return lab_from_lin(srgb2lin(c8))
def luma(c8):
    c = np.asarray(c8, float); return 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]
def word_rgb(w, dac):
    w = np.asarray(w)
    return np.stack([dac[(w >> 1) & 7], dac[(w >> 5) & 7], dac[(w >> 9) & 7]], -1).astype(float)
def word_of(rgb):  # today's generator: truncation
    r, g, b = (int(v) for v in rgb)
    return ((b >> 5) << 9) | ((g >> 5) << 5) | ((r >> 5) << 1)

# ------------------------------------------------------------------ WAD (little-endian)
class Wad:
    def __init__(self, path):
        d = Path(path).read_bytes()
        assert d[:4] in (b"IWAD", b"PWAD"), "expected a little-endian Doom IWAD"
        n, ofs = struct.unpack_from("<ii", d, 4)
        self.d = d
        self.dir = []
        for i in range(n):
            p, sz, name = struct.unpack_from("<ii8s", d, ofs + 16 * i)
            self.dir.append((name.split(b"\0")[0].decode("ascii", "replace").upper(), p, sz))
    def lump(self, name, start=0):
        for i in range(start, len(self.dir)):
            if self.dir[i][0] == name:
                n, p, sz = self.dir[i]; return self.d[p:p + sz]
        return None
    def index(self, name):
        return next(i for i, e in enumerate(self.dir) if e[0] == name)
    def span(self, a, b):
        i, j = self.index(a), self.index(b)
        return {n: self.d[p:p + sz] for n, p, sz in self.dir[i + 1:j] if sz > 0}
    def map_lumps(self, m):
        i = self.index(m)
        return {n: self.d[p:p + sz] for n, p, sz in self.dir[i + 1:i + 11]}

def patch_pixels(data):
    """-> (w,h, array h x w of index or -1)"""
    w, h, lo, to = struct.unpack_from("<hhhh", data, 0)
    img = -np.ones((h, w), np.int16)
    for x in range(w):
        p = struct.unpack_from("<i", data, 8 + 4 * x)[0]
        guard = 0
        while p < len(data) and data[p] != 255 and guard < 256:
            top, ln = data[p], data[p + 1]
            col = np.frombuffer(data, np.uint8, ln, p + 3)
            y0, y1 = top, min(h, top + ln)
            if y1 > y0:
                img[y0:y1, x] = col[:y1 - y0]
            p += ln + 4; guard += 1
    return img

def texture_hists(w):
    pn = w.lump("PNAMES"); n = struct.unpack_from("<i", pn, 0)[0]
    pnames = [pn[4 + 8 * i:12 + 8 * i].split(b"\0")[0].decode().upper() for i in range(n)]
    patches = {}
    i0, i1 = w.index("P_START"), w.index("P_END")
    for name, p, sz in w.dir[i0 + 1:i1]:
        if sz > 8: patches[name] = w.d[p:p + sz]
    cache, out = {}, {}
    for tl in ("TEXTURE1", "TEXTURE2"):
        t = w.lump(tl)
        if not t: continue
        cnt = struct.unpack_from("<i", t, 0)[0]
        for k in range(cnt):
            o = struct.unpack_from("<i", t, 4 + 4 * k)[0]
            name = t[o:o + 8].split(b"\0")[0].decode().upper()
            tw, th = struct.unpack_from("<hh", t, o + 12)
            npch = struct.unpack_from("<h", t, o + 20)[0]
            canvas = -np.ones((th, tw), np.int16)
            for q in range(npch):
                ox, oy, pi = struct.unpack_from("<hhh", t, o + 22 + 10 * q)
                pname = pnames[pi]
                if pname not in patches: continue
                if pname not in cache: cache[pname] = patch_pixels(patches[pname])
                img = cache[pname]; ph, pw = img.shape
                x0, y0 = max(ox, 0), max(oy, 0); x1, y1 = min(ox + pw, tw), min(oy + ph, th)
                if x1 <= x0 or y1 <= y0: continue
                sub = img[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
                m = sub >= 0
                canvas[y0:y1, x0:x1][m] = sub[m]
            v = canvas[canvas >= 0]
            out[name] = np.bincount(v, minlength=256).astype(float) / max(len(v), 1)
    return out

def flat_rep(w, pal8):
    flats = w.span("F_START", "F_END") if "F_START" in [e[0] for e in w.dir] else w.span("FF_START", "FF_END")
    lab = to_lab(pal8); out = {}
    for name, data in flats.items():
        if len(data) != 4096: continue
        v = np.frombuffer(data, np.uint8)
        mean = lin2srgb(srgb2lin(pal8[v]).mean(0))
        out[name] = int(np.argmin(((lab - to_lab(mean)) ** 2).sum(-1)))
    if "NUKAGE1" in out: out["NUKAGE1"] = 118   # FLAT_NUKAGE1_COLOR in the R89 build flags
    return out

def sprite_hist(w, prefix):
    i0 = next(i for i, e in enumerate(w.dir) if e[0] in ("S_START", "SS_START"))
    i1 = next(i for i, e in enumerate(w.dir) if e[0] in ("S_END", "SS_END"))
    for n, p, sz in w.dir[i0 + 1:i1]:
        if n.startswith(prefix + "A") and sz > 8:
            img = patch_pixels(w.d[p:p + sz]); v = img[img >= 0]
            return np.bincount(v, minlength=256).astype(float) / max(len(v), 1)
    return None

def wall_levels(light):
    """Doom distance shading: startmap=(15-(light>>4))*4, nearer walls up to ~20 levels brighter."""
    start = min(31, max(0, (15 - (light >> 4)) * 4))
    lv = np.arange(max(0, start - 20), start + 1)
    return lv, np.full(len(lv), 1.0 / len(lv))

def flat_level(light):
    return int(min(31, max(0, (15 - (light >> 4)) * 4 - 8)))

def map_weights(w, m, tex, frep, spr_cache):
    L = w.map_lumps(m)
    vx = np.frombuffer(L["VERTEXES"], "<i2").reshape(-1, 2).astype(float)
    sec = [struct.unpack_from("<hh8s8shhh", L["SECTORS"], 26 * i) for i in range(len(L["SECTORS"]) // 26)]
    sd = [struct.unpack_from("<hh8s8s8sh", L["SIDEDEFS"], 30 * i) for i in range(len(L["SIDEDEFS"]) // 30)]
    ld = [struct.unpack_from("<hhhhhhh", L["LINEDEFS"], 14 * i) for i in range(len(L["LINEDEFS"]) // 14)]
    nm = lambda b: b.split(b"\0")[0].decode().upper()
    walls = np.zeros((34, 256)); flats = np.zeros((34, 256)); sprites = np.zeros((34, 256))
    area = np.zeros(len(sec))
    for v1, v2, fl, sp, tg, s0, s1 in ld:
        a, b = vx[v1], vx[v2]; length = math.hypot(*(b - a))
        cross = a[0] * b[1] - a[1] * b[0]
        sides = [(s0, s1), (s1, s0)] if s1 != -1 else [(s0, -1)]
        for k, (sa, sb) in enumerate(sides):
            if sa < 0: continue
            fs = sd[sa][5]; area[fs] += cross if k == 0 else -cross
            fh, ch, light = sec[fs][0], sec[fs][1], sec[fs][4]
            parts = []
            if sb < 0:
                parts.append((nm(sd[sa][4]), ch - fh))
            else:
                bs = sd[sb][5]; bfh, bch = sec[bs][0], sec[bs][1]
                if bch < ch and nm(sec[bs][3]) != "F_SKY1": parts.append((nm(sd[sa][2]), ch - bch))
                if bfh > fh: parts.append((nm(sd[sa][3]), bfh - fh))
            lv, lw = wall_levels(light)
            for t, hgt in parts:
                if t in ("-", "") or t not in tex or hgt <= 0: continue
                walls[lv] += np.outer(lw, tex[t]) * (length * hgt)
    for i, s in enumerate(sec):
        fh, ch, fpic, cpic, light = s[0], s[1], nm(s[2]), nm(s[3]), s[4]
        a = abs(area[i]) / 2
        lvl = flat_level(light)
        for pic in (fpic, cpic):
            if pic == "F_SKY1" or pic not in frep: continue
            flats[lvl, frep[pic]] += a
    things = L["THINGS"]
    for i in range(len(things) // 10):
        x, y, ang, typ, flg = struct.unpack_from("<hhhhh", things, 10 * i)
        if typ in (1, 2, 3, 4, 11) or typ not in THING_SPR or not (flg & 4) or (flg & 16): continue  # UV/hard, single player
        pre = THING_SPR[typ]
        if pre not in spr_cache: spr_cache[pre] = sprite_hist(w, pre)
        h = spr_cache[pre]
        if h is not None:
            lv, lw = wall_levels(160)
            sprites[lv] += np.outer(lw, h)
    out = np.zeros((34, 256)); outf = np.zeros((34, 256)); cats = {}
    for arr, key, dst in ((walls, "walls", out), (sprites, "sprites", out), (flats, "flats", outf)):
        cats[key] = SHARE[key] * arr / arr.sum() if arr.sum() > 0 else np.zeros((34, 256))
        dst += cats[key]
    return out, outf, cats

def post(cm, W):
    h = np.zeros(256)
    for l in range(34):
        np.add.at(h, cm[l], W[l])
    return h

# ------------------------------------------------------------------ R89 tables
def parse_tables(path):
    txt = Path(path).read_text()
    def arr(name, shape):
        m = re.search(r"\b" + re.escape(name) + r"(\[[^\]]*\])+=\{(.*?)\};", txt, re.S)
        assert m, name
        v = np.array([int(x) for x in re.findall(r"-?\d+", m.group(2))])
        assert v.size == int(np.prod(shape)), (name, v.size, shape)
        return v.reshape(shape)
    init = re.search(r"r59_color_tables\[R59_COLOR_MODES\]=\{(.*?)\n\};", txt, re.S).group(1)
    modes = []
    for row in re.findall(r"\{([^{}]+)\}", init):
        f = [x.strip() for x in row.split(",")]
        modes.append(dict(pal0=arr(f[0], (14, 16))[0], pal1=arr(f[1], (14, 16))[0],
                          pairs_even=arr(f[2], (16, 2)), pairs_odd=arr(f[3], (16, 2)),
                          wall_even=arr(f[4], (256,)), wall_odd=arr(f[5], (256,)),
                          flat_even=arr(f[6], (256,)), flat_odd=arr(f[7], (256,)),
                          comp_even=arr(f[8], (34, 256)), comp_odd=arr(f[9], (34, 256)), names=f))
    return modes

# ------------------------------------------------------------------ display model / evaluation
def code_lin(pal, pairs, dac):
    """linear RGB shown by each code 0..15 of one plane (M50 of the pair)."""
    rgb = word_rgb(pal, dac)
    return (srgb2lin(rgb[pairs[:, 0]]) + srgb2lin(rgb[pairs[:, 1]])) / 2

def evaluate(tset, pal8, cm, Ww, Wf, dac):
    """weighted dE76 of what the view shows vs Doom's colour; walls/sprites via comp[level][src], flats via flat maps."""
    ce = code_lin(tset["pal0"], tset["pairs_even"], dac); co = code_lin(tset["pal1"], tset["pairs_odd"], dac)
    tgt = to_lab(pal8)
    errs, wts, per_c = [], [], np.zeros(256); per_w = np.zeros(256)
    colw = {"walls": [0.0, 0.0], "flats": [0.0, 0.0]}   # weighted sum of even/odd column dE, weight
    for l in range(34):
        if Ww[l].sum() > 0:
            le, lo = lab_from_lin(ce[tset["comp_even"][l]]), lab_from_lin(co[tset["comp_odd"][l]])
            colw["walls"][0] += float((np.sqrt(((le - lo) ** 2).sum(-1)) * Ww[l]).sum()); colw["walls"][1] += float(Ww[l].sum())
            shown = lab_from_lin((ce[tset["comp_even"][l]] + co[tset["comp_odd"][l]]) / 2)
            e = np.sqrt(((shown - tgt[cm[l]]) ** 2).sum(-1))
            errs.append(e); wts.append(Ww[l]); np.add.at(per_c, cm[l], e * Ww[l]); np.add.at(per_w, cm[l], Ww[l])
        if Wf[l].sum() > 0:
            c = cm[l]
            le, lo = lab_from_lin(ce[tset["flat_even"][c]]), lab_from_lin(co[tset["flat_odd"][c]])
            colw["flats"][0] += float((np.sqrt(((le - lo) ** 2).sum(-1)) * Wf[l]).sum()); colw["flats"][1] += float(Wf[l].sum())
            shown = lab_from_lin((ce[tset["flat_even"][c]] + co[tset["flat_odd"][c]]) / 2)
            e = np.sqrt(((shown - tgt[c]) ** 2).sum(-1))
            errs.append(e); wts.append(Wf[l]); np.add.at(per_c, c, e * Wf[l]); np.add.at(per_w, c, Wf[l])
    e = np.concatenate(errs); w = np.concatenate(wts); w = w / w.sum()
    order = np.argsort(e); cw = np.cumsum(w[order])
    p90 = float(e[order][np.searchsorted(cw, 0.9)])
    with np.errstate(invalid="ignore", divide="ignore"):
        pc = np.where(per_w > 0, per_c / per_w, 0)
    worst = sorted(((float(per_w[c] / per_w.sum()) * pc[c], c) for c in range(256) if per_w[c] > 0), reverse=True)[:6]
    return dict(mean=float((e * w).sum()), p90=p90,
                col_walls=colw["walls"][0] / max(colw["walls"][1], 1e-12), col_flats=colw["flats"][0] / max(colw["flats"][1], 1e-12), over10=float(w[e > 10].sum()), over20=float(w[e > 20].sum()),
                worst=[dict(c=int(c), dE=round(float(pc[c]), 1), weight=round(float(per_w[c] / per_w.sum()), 4)) for _, c in worst])

# ------------------------------------------------------------------ generator (R52 objective + R53-style M50)
class Gen:
    def __init__(self, pal8, H, cand_words, dac, tau_l=32.0, mu_l=0.10, lam=0.0):
        self.T = to_lab(pal8); self.W = H / H.sum(); self.words = np.array(cand_words)
        self.rgb = word_rgb(self.words, dac); self.lin = srgb2lin(self.rgb); self.lum = luma(self.rgb)
        self.lab = lab_from_lin(self.lin)
        self.tau_l, self.mu_l, self.lam = tau_l, mu_l, lam
    def pair_cost(self, p0, p1, lam):
        A, B = self.lin[p0], self.lin[p1]
        lab = lab_from_lin((A[:, None] + B[None]) / 2)
        pen = self.mu_l * np.maximum(0, np.abs(self.lum[p0][:, None] - self.lum[p1][None]) - self.tau_l) ** 2
        if lam:   # R90: even/odd column contrast (vertical striping) as part of the objective
            pen = pen + lam * np.sqrt(((self.lab[p0][:, None] - self.lab[p1][None]) ** 2).sum(-1))
        return np.sqrt(((lab[None] - self.T[:, None, None]) ** 2).sum(-1)) + pen[None]
    def cost(self, p0, p1):
        c = self.pair_cost(p0, p1, self.lam)
        flat = c.reshape(256, -1); arg = flat.argmin(1)
        return float((flat[np.arange(256), arg] * self.W).sum()), arg, len(p1)
    def run(self, slots=15, refine=1):
        live = np.where(self.W > 0)[0]
        cand = range(len(self.words)); ch = ([], [])
        for step in range(2 * slots):
            k = step % 2; best = (1e18, None)
            for c in cand:
                if c in ch[k]: continue
                t = (ch[0] + [c], ch[1]) if k == 0 else (ch[0], ch[1] + [c])
                if not t[0] or not t[1]:
                    v = float((np.sqrt(((to_lab(self.rgb[c]) - self.T) ** 2).sum(-1)) * self.W).sum())
                else:
                    v = self.cost(*t)[0]
                if v < best[0]: best = (v, c)
            ch[k].append(best[1])
        for _ in range(refine):
            for k in (0, 1):
                for pos in range(slots):
                    cur = self.cost(*ch)[0]; keep = ch[k][pos]
                    for c in cand:
                        if c in ch[k]: continue
                        old = ch[k][pos]; ch[k][pos] = c
                        v = self.cost(*ch)[0]
                        if v < cur - 1e-9: cur, keep = v, c
                        ch[k][pos] = old
                    ch[k][pos] = keep
        _, arg, nB = self.cost(*ch)
        even = arg // nB + 1; odd = arg % nB + 1
        self.chosen = ch
        pal0 = np.zeros(16, int); pal1 = np.zeros(16, int)
        pal0[1:] = self.words[ch[0]]; pal1[1:] = self.words[ch[1]]
        return pal0, pal1, even, odd

def companions(pal, codes, pal8, H, dac, ratio=0.5, limit=38.0):
    """R53-style M50 partner per slot (same palette): keep a partner only if it lowers the weighted error."""
    rgb = word_rgb(pal, dac); lin = srgb2lin(rgb); T = to_lab(pal8); lab = lab_from_lin(lin); lum = luma(rgb)
    pairs = np.array([[i, i] for i in range(16)])
    for i in range(1, 16):
        where = np.where(codes == i)[0]
        if not len(where) or H[where].sum() <= 0: continue
        w = H[where]; base = float((np.sqrt(((lab[i] - T[where]) ** 2).sum(-1)) * w).sum()); best = (base, i)
        for j in range(1, 16):
            if j == i: continue
            if np.sqrt(((lab[i] - lab[j]) ** 2).sum()) > limit or abs(lum[i] - lum[j]) > limit: continue
            mix = lab_from_lin((1 - ratio) * lin[i] + ratio * lin[j])
            v = float((np.sqrt(((mix - T[where]) ** 2).sum(-1)) * w).sum())
            if v < best[0] - max(0.015, 0.012 * base) * w.sum(): best = (v, j)
        pairs[i] = [i, best[1]]
    return pairs

def build_set(pal8, cm, H, cand, gdac, refine):
    g = Gen(pal8, H, cand, DAC[gdac]); pal0, pal1, even, odd = g.run(refine=refine)
    pe = companions(pal0, even, pal8, H, DAC[gdac]); po = companions(pal1, odd, pal8, H, DAC[gdac])
    comp_e = np.stack([even[cm[l]] for l in range(34)]); comp_o = np.stack([odd[cm[l]] for l in range(34)])
    return dict(pal0=pal0, pal1=pal1, pairs_even=pe, pairs_odd=po, wall_even=even, wall_odd=odd,
                flat_even=even, flat_odd=odd, comp_even=comp_e, comp_odd=comp_o)

def build_set3(pal8, cm, H, cand, gdac, lam_w, lam_f, refine):
    """R90 round 3: palettes chosen with the wall contrast weight; flats get their own maps with lam_f."""
    g = Gen(pal8, H, cand, DAC[gdac], lam=lam_w); pal0, pal1, even, odd = g.run(refine=refine)
    fc = g.pair_cost(g.chosen[0], g.chosen[1], lam_f).reshape(256, -1).argmin(1)
    feven = fc // len(g.chosen[1]) + 1; fodd = fc % len(g.chosen[1]) + 1
    pe = companions(pal0, even, pal8, H, DAC[gdac]); po = companions(pal1, odd, pal8, H, DAC[gdac])
    return dict(pal0=pal0, pal1=pal1, pairs_even=pe, pairs_odd=po, wall_even=even, wall_odd=odd,
                flat_even=feven, flat_odd=fodd,
                comp_even=np.stack([even[cm[l]] for l in range(34)]), comp_odd=np.stack([odd[cm[l]] for l in range(34)]))

BANDS = {"bright": range(0, 8), "mid": range(8, 20), "dark": range(20, 34)}

def breakdown(tset, pal8, cm, cats, dac):
    """weighted dE per category (walls, sprites, flats) and light band, plus even/odd column contrast."""
    ce = code_lin(tset["pal0"], tset["pairs_even"], dac); co = code_lin(tset["pal1"], tset["pairs_odd"], dac)
    tgt = to_lab(pal8); res = {}
    for cat in ("walls", "sprites", "flats"):
        W = cats[cat]; acc = {b: [0.0, 0.0] for b in BANDS}; col = [0.0, 0.0]
        for l in range(34):
            if W[l].sum() <= 0: continue
            if cat == "flats":
                c = cm[l]; we = ce[tset["flat_even"][c]]; wo = co[tset["flat_odd"][c]]; target = tgt[c]
            else:
                we = ce[tset["comp_even"][l]]; wo = co[tset["comp_odd"][l]]; target = tgt[cm[l]]
            e = np.sqrt(((lab_from_lin((we + wo) / 2) - target) ** 2).sum(-1))
            k = np.sqrt(((lab_from_lin(we) - lab_from_lin(wo)) ** 2).sum(-1))
            b = next(n for n, r in BANDS.items() if l in r)
            acc[b][0] += float((e * W[l]).sum()); acc[b][1] += float(W[l].sum())
            col[0] += float((k * W[l]).sum()); col[1] += float(W[l].sum())
        res[cat] = {b: (v[0] / v[1] if v[1] else None) for b, v in acc.items()}
        res[cat]["all"] = sum(v[0] for v in acc.values()) / max(sum(v[1] for v in acc.values()), 1e-12)
        res[cat]["col"] = col[0] / max(col[1], 1e-12)
    return res

def main3(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    w = Wad(a.wad)
    pal8 = np.frombuffer(w.lump("PLAYPAL")[:768], np.uint8).reshape(256, 3).astype(float)
    cm = np.frombuffer(w.lump("COLORMAP"), np.uint8)[:34 * 256].reshape(34, 256)
    tex = texture_hists(w); frep = flat_rep(w, pal8); spr = {}
    modes = parse_tables(a.tables)
    maps = [m for m in a.maps.split(",") if m]
    W = {m: map_weights(w, m, tex, frep, spr) for m in maps}
    all_words = [((b << 9) | (g << 5) | (r << 1)) for b in range(8) for g in range(8) for r in range(8)][1:]
    def train_hist(train, beta):
        boost = np.ones(34); boost[20:] += beta
        return sum(post(cm, W[m][0] * boost[:, None]) + post(cm, W[m][1] * boost[:, None]) for m in train)
    folds = {"odd": [m for m in maps if int(m[-1]) % 2 == 1], "even": [m for m in maps if int(m[-1]) % 2 == 0]}
    configs = [(lw, lf, b) for (lw, lf, b) in
               [(0.0, 1.0, 0.0), (0.15, 1.0, 0.0), (0.3, 1.0, 0.0), (0.6, 1.0, 0.0),
                (0.0, 1.0, 1.5), (0.15, 1.0, 1.5), (0.3, 1.0, 1.5), (0.6, 1.0, 1.5), (1.0, 1.5, 1.5)]]
    names = ["R89 0 Hybrid Blue", "R89 1 A2", "R89 2 L3", "R89 3 HN"]
    cand = {names[i]: {m: md for m in maps} for i, md in enumerate(modes)}
    for lw, lf, b in configs:
        key = "GEN lw%.2f lf%.1f dark+%.1f" % (lw, lf, b)
        sets = {k: build_set3(pal8, cm, train_hist(tr, b), all_words, "HW", lw, lf, a.refine) for k, tr in folds.items()}
        cand[key] = {m: (sets["even"] if int(m[-1]) % 2 == 1 else sets["odd"]) for m in maps}   # held-out
        cand[key]["_pal"] = {k: {"pal0": list(map(int, s["pal0"])), "pal1": list(map(int, s["pal1"]))} for k, s in sets.items()}
        print(key, "%.0fs" % (time.time() - t0), flush=True)
    rep_ = {"bands": {k: [r.start, r.stop - 1] for k, r in BANDS.items()}, "dac": "HW", "candidates": {}}
    for key, per in cand.items():
        agg = {}
        for m in maps:
            r = breakdown(per[m], pal8, cm, W[m][2], DAC["HW"])
            for cat, d in r.items():
                for k, v in d.items():
                    if v is not None: agg.setdefault(cat, {}).setdefault(k, []).append(v)
            ov = evaluate(per[m], pal8, cm, W[m][0], W[m][1], DAC["HW"])
            agg.setdefault("overall", {}).setdefault("mean", []).append(ov["mean"])
        rep_["candidates"][key] = {c: {k: float(np.mean(v)) for k, v in d.items()} for c, d in agg.items()}
        if "_pal" in per: rep_["candidates"][key]["palettes"] = per["_pal"]
    (out / "round3.json").write_text(json.dumps(rep_, indent=1))
    hdr = ["candidate", "overall", "walls dark", "walls mid", "walls bright", "sprites", "flats", "col walls", "col flats"]
    L = ["# R90 round 3: fidelity vs column contrast (held-out, measured MD DAC)", "",
         "Mean over E1M1-E1M9 of weighted CIELAB dE76 vs Doom colours (lower = more faithful); generated sets are "
         "always evaluated on maps they were NOT trained on. col = dE between even and odd columns (higher = more vertical striping).",
         "Bands: bright = COLORMAP 0-7, mid = 8-19, dark = 20-33. lw/lf = contrast weight walls/flats, dark+ = extra weight on dark levels.", "",
         "| " + " | ".join(hdr) + " |", "|---|" + "---:|" * (len(hdr) - 1)]
    for key, d in rep_["candidates"].items():
        f = lambda c, k: ("%.1f" % d[c][k]) if c in d and k in d[c] else "-"
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (key, f("overall", "mean"), f("walls", "dark"), f("walls", "mid"),
                 f("walls", "bright"), f("sprites", "all"), f("flats", "all"), f("walls", "col"), f("flats", "col")))
    (out / "ROUND3.md").write_text("\n".join(L) + "\n"); print("\n".join(L)); print("total %.0fs" % (time.time() - t0))


def refit_flats(tset, pal8, dac, lf):
    """R90 round 4: keep CRAM, M50 pairs, walls and sprites; choose for every colour the (even, odd) code pair,
    codes 1..15 only (no transparent black), minimising dE(target, column average) + lf * dE(even, odd)."""
    ce = code_lin(tset["pal0"], tset["pairs_even"], dac)[1:]; co = code_lin(tset["pal1"], tset["pairs_odd"], dac)[1:]
    le, lo = lab_from_lin(ce), lab_from_lin(co)
    mix = lab_from_lin((ce[:, None] + co[None]) / 2)                      # 15 x 15
    contrast = np.sqrt(((le[:, None] - lo[None]) ** 2).sum(-1))           # 15 x 15
    tgt = to_lab(pal8)
    cost = np.sqrt(((mix[None] - tgt[:, None, None]) ** 2).sum(-1)) + lf * contrast[None]
    arg = cost.reshape(256, -1).argmin(1)
    out = dict(tset); out["flat_even"] = arg // 15 + 1; out["flat_odd"] = arg % 15 + 1
    return out

def main4(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    w = Wad(a.wad)
    pal8 = np.frombuffer(w.lump("PLAYPAL")[:768], np.uint8).reshape(256, 3).astype(float)
    cm = np.frombuffer(w.lump("COLORMAP"), np.uint8)[:34 * 256].reshape(34, 256)
    tex = texture_hists(w); frep = flat_rep(w, pal8); spr = {}
    modes = parse_tables(a.tables)
    maps = [m for m in a.maps.split(",") if m]
    W = {m: map_weights(w, m, tex, frep, spr) for m in maps}
    names = ["R89 0 Hybrid Blue", "R89 1 A2", "R89 2 L3", "R89 3 HN"]
    rep_ = {"candidates": {}, "luts": {}}
    def score(ts):
        agg = {}
        for m in maps:
            r = breakdown(ts, pal8, cm, W[m][2], DAC["HW"])
            agg.setdefault("flats", []).append(r["flats"]["all"]); agg.setdefault("col_flats", []).append(r["flats"]["col"])
            agg.setdefault("walls", []).append(r["walls"]["all"]); agg.setdefault("sprites", []).append(r["sprites"]["all"])
            for b in ("bright", "mid", "dark"):
                if r["flats"][b] is not None: agg.setdefault("flats_" + b, []).append(r["flats"][b])
            agg.setdefault("overall", []).append(evaluate(ts, pal8, cm, W[m][0], W[m][1], DAC["HW"])["mean"])
        return {k: float(np.mean(v)) for k, v in agg.items()}
    for i, md in enumerate(modes):
        rep_["candidates"][names[i] + " (shipped)"] = score(md)
        for lf in (0.25, 0.5, 1.0, 1.5, 2.5):
            ts = refit_flats(md, pal8, DAC["HW"], lf)
            key = "%s flats lf%.2f" % (names[i], lf)
            sc = score(ts); sc["changed_entries"] = int((ts["flat_even"] != md["flat_even"]).sum() + (ts["flat_odd"] != md["flat_odd"]).sum())
            rep_["candidates"][key] = sc
            rep_["luts"][key] = {"flat_even": list(map(int, ts["flat_even"])), "flat_odd": list(map(int, ts["flat_odd"]))}
        print(names[i], "%.0fs" % (time.time() - t0), flush=True)
    (out / "round4.json").write_text(json.dumps(rep_, indent=1))
    hdr = ["candidate", "flats dE", "flats dark", "flats mid", "flats bright", "col flats", "walls", "sprites", "overall", "changed"]
    L = ["# R90 round 4: flat LUTs only (CRAM, M50 pairs, walls and sprites of each R89 mode unchanged)", "",
         "Mean over E1M1-E1M9, measured MD DAC. flats dE = weighted CIELAB dE76 vs Doom colour (lower = more faithful); "
         "col flats = dE between even and odd columns on floors/ceilings (higher = more vertical striping). "
         "lf = striping weight in the refit; codes 1..15 only (never transparent black). changed = LUT entries that differ from R89 (of 512).", "",
         "| " + " | ".join(hdr) + " |", "|---|" + "---:|" * (len(hdr) - 1)]
    for key, d in rep_["candidates"].items():
        g = lambda k: ("%.1f" % d[k]) if k in d else "-"
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (key, g("flats"), g("flats_dark"), g("flats_mid"), g("flats_bright"),
                 g("col_flats"), g("walls"), g("sprites"), g("overall"), d.get("changed_entries", "-")))
    (out / "ROUND4.md").write_text("\n".join(L) + "\n"); print("\n".join(L)); print("total %.0fs" % (time.time() - t0))


def refit_flats_safe(tset, pal8, dac, lam=0.25, min_gain=1.0, dl_max=6.0, chroma_keep=0.7):
    """R90 round 5 (fix for the light-grey floors of round 4): per-colour guarded refit.
    An entry only changes if, for THAT colour, the new (even, odd) pair is better than R89 in target error by
    >= min_gain, does not add column contrast beyond max(R89's, 3), keeps lightness within max(R89's |dL|, dl_max)
    of the target and keeps at least chroma_keep of the target chroma (or R89's chroma). Codes 1..15 only."""
    ce = code_lin(tset["pal0"], tset["pairs_even"], dac); co = code_lin(tset["pal1"], tset["pairs_odd"], dac)
    le, lo = lab_from_lin(ce), lab_from_lin(co)
    mix = lab_from_lin((ce[:, None] + co[None]) / 2)
    con = np.sqrt(((le[:, None] - lo[None]) ** 2).sum(-1))
    tgt = to_lab(pal8); fe = np.array(tset["flat_even"]).copy(); fo = np.array(tset["flat_odd"]).copy(); changed = []
    for c in range(256):
        e0, o0 = fe[c], fo[c]
        err = np.sqrt(((mix - tgt[c]) ** 2).sum(-1)); dl = np.abs(mix[..., 0] - tgt[c, 0]); ch = np.hypot(mix[..., 1], mix[..., 2])
        tch = float(np.hypot(*tgt[c, 1:]))
        ok = (err <= err[e0, o0] - min_gain) & (con <= max(con[e0, o0], 3.0)) & (dl <= max(dl[e0, o0], dl_max))
        if tch > 10:
            ok &= ch >= min(ch[e0, o0], chroma_keep * tch)
        ok[0, :] = False; ok[:, 0] = False
        if not (tgt[c, 0] > 55 and tch < 12):   # never turn a colour into light grey unless Doom's colour is light grey
            ok &= ~((mix[..., 0] > 55) & (ch < 12))
        if not ok.any(): continue
        score = np.where(ok, err + lam * con, np.inf); i, j = np.unravel_index(np.argmin(score), score.shape)
        changed.append(dict(c=c, old=[int(e0), int(o0)], new=[int(i), int(j)], err=[round(float(err[e0, o0]), 1), round(float(err[i, j]), 1)],
                            contrast=[round(float(con[e0, o0]), 1), round(float(con[i, j]), 1)]))
        fe[c], fo[c] = i, j
    out = dict(tset); out["flat_even"] = fe; out["flat_odd"] = fo
    return out, changed

def light_grey(tset, dac):
    ce = code_lin(tset["pal0"], tset["pairs_even"], dac); co = code_lin(tset["pal1"], tset["pairs_odd"], dac)
    lab = lab_from_lin((ce[np.array(tset["flat_even"])] + co[np.array(tset["flat_odd"])]) / 2)
    return int(((lab[:, 0] > 55) & (np.hypot(lab[:, 1], lab[:, 2]) < 12)).sum())

def main5(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True); t0 = time.time()
    w = Wad(a.wad)
    pal8 = np.frombuffer(w.lump("PLAYPAL")[:768], np.uint8).reshape(256, 3).astype(float)
    cm = np.frombuffer(w.lump("COLORMAP"), np.uint8)[:34 * 256].reshape(34, 256)
    tex = texture_hists(w); frep = flat_rep(w, pal8); spr = {}
    modes = parse_tables(a.tables); maps = [m for m in a.maps.split(",") if m]
    W = {m: map_weights(w, m, tex, frep, spr) for m in maps}
    names = ["R89 0 Hybrid Blue", "R89 1 A2", "R89 2 L3", "R89 3 HN"]; arrays = ["r77_h_flat", "r76_a_flat", "r76_l_flat", "r76_n_flat"]
    tgt = to_lab(pal8)
    rep_ = {"candidates": {}, "luts": {}, "changes": {}}
    def score(ts):
        agg = {}
        for m in maps:
            r = breakdown(ts, pal8, cm, W[m][2], DAC["HW"])
            agg.setdefault("flats", []).append(r["flats"]["all"]); agg.setdefault("col_flats", []).append(r["flats"]["col"])
        return {k: float(np.mean(v)) for k, v in agg.items()}
    for i, md in enumerate(modes):
        ts, ch = refit_flats_safe(md, pal8, DAC["HW"])
        s0, s1 = score(md), score(ts)
        # per-colour guarantee over all 256 colours (not weighted): no colour gets worse in error or contrast
        ce = code_lin(md["pal0"], md["pairs_even"], DAC["HW"]); co = code_lin(md["pal1"], md["pairs_odd"], DAC["HW"])
        def per(t):
            e_, o_ = np.array(t["flat_even"]), np.array(t["flat_odd"])
            lab = lab_from_lin((ce[e_] + co[o_]) / 2)
            return np.sqrt(((lab - tgt) ** 2).sum(-1)), np.sqrt(((lab_from_lin(ce[e_]) - lab_from_lin(co[o_])) ** 2).sum(-1))
        e0, k0 = per(md); e1, k1 = per(ts)
        rep_["candidates"][names[i]] = dict(shipped=s0, safe=s1, changed=len(ch), light_grey=[light_grey(md, DAC["HW"]), light_grey(ts, DAC["HW"])],
                                           worse_error=int((e1 > e0 + 1e-9).sum()), worse_contrast=int((k1 > np.maximum(k0, 3.0) + 1e-9).sum()),
                                           unweighted_mean_error=[float(e0.mean()), float(e1.mean())])
        rep_["luts"][arrays[i] + "_even"] = list(map(int, ts["flat_even"])); rep_["luts"][arrays[i] + "_odd"] = list(map(int, ts["flat_odd"]))
        rep_["changes"][names[i]] = ch
    (out / "round5.json").write_text(json.dumps(rep_, indent=1))
    L = ["# R90 round 5: guarded flat LUT refit (fix for the light-grey floors of round 4)", "",
         "Per colour, an entry changes only if it beats R89 in target error by >= 1 dE without adding column contrast, "
         "without moving lightness and without washing out colour. Weighted numbers are the screen proxy (E1M1-E1M9, measured DAC); "
         "the guarantee columns count all 256 colours, unweighted.", "",
         "| mode | flats dE R89 -> safe | col flats R89 -> safe | changed (of 256) | light-grey entries R89 -> safe | colours worse in error | colours worse in contrast | unweighted mean dE |",
         "|---|---|---|---:|---|---:|---:|---|"]
    for k, d in rep_["candidates"].items():
        L.append("| %s | %.1f -> %.1f | %.1f -> %.1f | %d | %d -> %d | %d | %d | %.1f -> %.1f |" % (k, d["shipped"]["flats"], d["safe"]["flats"],
                 d["shipped"]["col_flats"], d["safe"]["col_flats"], d["changed"], d["light_grey"][0], d["light_grey"][1],
                 d["worse_error"], d["worse_contrast"], d["unweighted_mean_error"][0], d["unweighted_mean_error"][1]))
    (out / "ROUND5.md").write_text("\n".join(L) + "\n"); print("\n".join(L)); print("total %.0fs" % (time.time() - t0))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--wad", required=True); ap.add_argument("--tables", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--refine", type=int, default=1)
    ap.add_argument("--maps", default=",".join(MAPS)); ap.add_argument("--round3", action="store_true")
    ap.add_argument("--round4", action="store_true"); ap.add_argument("--round5", action="store_true")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.round5:
        return main5(a)
    if a.round4:
        return main4(a)
    if a.round3:
        return main3(a)
    t0 = time.time()
    w = Wad(a.wad)
    pal8 = np.frombuffer(w.lump("PLAYPAL")[:768], np.uint8).reshape(256, 3).astype(float)
    cm = np.frombuffer(w.lump("COLORMAP"), np.uint8)[:34 * 256].reshape(34, 256)
    tex = texture_hists(w); frep = flat_rep(w, pal8); spr = {}
    modes = parse_tables(a.tables)
    mode_names = ["0 Hybrid Blue", "1 A2 N25A-M50", "2 L3 L32F-M50", "3 HN L32F near flats"]
    maps = [m for m in a.maps.split(",") if m]
    W = {m: map_weights(w, m, tex, frep, spr) for m in maps}
    Hep = sum(post(cm, W[m][0]) + post(cm, W[m][1]) for m in maps)
    cur_words = sorted({word_of(pal8[c]) for c in range(256)} - {0})
    all_words = [((b << 9) | (g << 5) | (r << 1)) for b in range(8) for g in range(8) for r in range(8)][1:]
    print("weights ready %.0fs; textures %d flats %d" % (time.time() - t0, len(tex), len(frep)), flush=True)
    sets = {"GEN-global": build_set(pal8, cm, Hep, cur_words, "LIN", a.refine),
            "GEN-global-HW": build_set(pal8, cm, Hep, all_words, "HW", a.refine)}
    folds = {"odd": [m for m in maps if int(m[-1]) % 2 == 1], "even": [m for m in maps if int(m[-1]) % 2 == 0]}
    cv = {}
    for k, train in folds.items():   # trained WITHOUT the maps it is evaluated on
        Ht = sum(post(cm, W[m][0]) + post(cm, W[m][1]) for m in train)
        cv[k] = build_set(pal8, cm, Ht, all_words, "HW", a.refine)
    print("global + cross-validation sets %.0fs" % (time.time() - t0), flush=True)
    rep = {"model": {"dac": {k: list(map(float, v)) for k, v in DAC.items()}, "shares": SHARE,
                     "metric": "CIELAB dE76 vs original 8-bit PLAYPAL, weighted by per-map screen proxy",
                     "caveat": "screen weights and light spread are proxies; DAC HW = commonly measured MD levels, not this user's TV"},
           "maps": {}}
    for m in maps:
        Ww, Wf = W[m]; Hm = post(cm, Ww) + post(cm, Wf)
        held = cv["even"] if int(m[-1]) % 2 == 1 else cv["odd"]
        sm = {"GEN-heldout-HW": held, "GEN-map-HW": build_set(pal8, cm, Hm, all_words, "HW", a.refine)}
        r = {}
        for dacn in ("HW", "LIN"):
            for i, md in enumerate(modes):
                r["R89 " + mode_names[i] + " @" + dacn] = evaluate(md, pal8, cm, Ww, Wf, DAC[dacn])
            for k, s in list(sets.items()) + list(sm.items()):
                r[k + " @" + dacn] = evaluate(s, pal8, cm, Ww, Wf, DAC[dacn])
        r["_palettes"] = {k: {"pal0": list(map(int, s["pal0"])), "pal1": list(map(int, s["pal1"]))} for k, s in sm.items()}
        rep["maps"][m] = r
        print(m, "done %.0fs" % (time.time() - t0), "R89 L3@HW %.1f  GEN-map-HW@HW %.1f" % (
            r["R89 2 L3 L32F-M50 @HW"]["mean"], r["GEN-map-HW @HW"]["mean"]), flush=True)
    rep["global_palettes"] = {k: {"pal0": list(map(int, s["pal0"])), "pal1": list(map(int, s["pal1"]))} for k, s in sets.items()}
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    rows = ["R89 0 Hybrid Blue", "R89 1 A2 N25A-M50", "R89 2 L3 L32F-M50", "R89 3 HN L32F near flats", "GEN-global", "GEN-global-HW", "GEN-heldout-HW", "GEN-map-HW"]
    L = ["# R90 colour analysis (offline, no ROM)", "", "Weighted mean CIELAB dE76 vs Doom's 8-bit colours (lower is better); "
         "evaluated with the measured MD DAC (HW). Per-map screen proxy: walls 50%, flats 40%, sprites 10%.", "",
         "| map | " + " | ".join(rows) + " |", "|---|" + "---:|" * len(rows)]
    for m in maps:
        r = rep["maps"][m]
        L.append("| %s | " % m + " | ".join("%.1f" % r[k + " @HW"]["mean"] for k in rows) + " |")
    L += ["", "p90 / share of screen with dE>10 (HW):", "", "| map | " + " | ".join(rows) + " |", "|---|" + "---:|" * len(rows)]
    for m in maps:
        r = rep["maps"][m]
        L.append("| %s | " % m + " | ".join("%.0f / %.0f%%" % (r[k + " @HW"]["p90"], 100 * r[k + " @HW"]["over10"]) for k in rows) + " |")
    L += ["", "Column contrast (weighted dE between even and odd sample columns: higher = more vertical striping), walls / flats, HW:", "",
          "| map | " + " | ".join(rows) + " |", "|---|" + "---:|" * len(rows)]
    for m in maps:
        r = rep["maps"][m]
        L.append("| %s | " % m + " | ".join("%.1f / %.1f" % (r[k + " @HW"]["col_walls"], r[k + " @HW"]["col_flats"]) for k in rows) + " |")
    L += ["", "Same table evaluated with the linear DAC the current generators assume (LIN):", "",
          "| map | " + " | ".join(rows) + " |", "|---|" + "---:|" * len(rows)]
    for m in maps:
        r = rep["maps"][m]
        L.append("| %s | " % m + " | ".join("%.1f" % r[k + " @LIN"]["mean"] for k in rows) + " |")
    (out / "REPORT.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    print("total %.0fs" % (time.time() - t0))

if __name__ == "__main__":
    sys.exit(main())
