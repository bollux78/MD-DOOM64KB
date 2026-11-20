#!/usr/bin/env python3
"""DREAD-MD D01 map converter: Doom WAD map -> C tables for the Dread-style renderer.

Output (one C file + header):
  - vertices, segs, subsectors, nodes, sectors, linedefs (collision) of one map
  - wall textures used by the map: composited from patches, width halved
    (the renderer draws 2-pixel-wide columns), height padded to a power of two,
    stored column-major, one copy per light bucket, one byte per texel = MD colour
    index doubled (c | c << 4) so a byte store paints both pixels of a column pair
  - floor / ceiling: one flat colour per sector (average of the flat), no texture
  - one 16-colour Mega Drive palette fitted (k-means) to everything the map uses

usage: conv.py WAD MAP OUTDIR
"""
import struct, sys, math
from pathlib import Path
import numpy as np

LIGHT_ROWS = (0, 5, 10, 16)          # COLORMAP rows used as light buckets (0 = full bright)


def bucket_of(light):
    row = max(0, min(31, (255 - light) // 8))
    return min(range(len(LIGHT_ROWS)), key=lambda i: abs(LIGHT_ROWS[i] - row))


class Wad:
    def __init__(self, path):
        d = Path(path).read_bytes()
        self.d = d
        n, off = struct.unpack_from("<4xII", d, 0)
        self.lumps = []
        for i in range(n):
            p, s, name = struct.unpack_from("<II8s", d, off + 16 * i)
            self.lumps.append((name.rstrip(b"\0").decode("ascii", "replace").upper(), p, s))

    def find(self, name, start=0):
        for i in range(start, len(self.lumps)):
            if self.lumps[i][0] == name:
                return i
        return -1

    def get(self, name):
        i = self.find(name)
        if i < 0:
            return None
        _, p, s = self.lumps[i]
        return self.d[p:p + s]

    def idx(self, i):
        _, p, s = self.lumps[i]
        return self.d[p:p + s]

    def range(self, a, b):
        """lumps between markers a..b (any of the names in tuples)"""
        out = {}
        inside = False
        for name, p, s in self.lumps:
            if name in a:
                inside = True
                continue
            if name in b:
                inside = False
                continue
            if inside and s:
                out[name] = self.d[p:p + s]
        return out


def name8(b):
    return b.rstrip(b"\0").decode("ascii", "replace").upper()


def read_patch(data):
    w, h, lo, to = struct.unpack_from("<HHhh", data, 0)
    img = np.full((h, w), -1, np.int16)
    cols = struct.unpack_from("<%dI" % w, data, 8)
    for x, c in enumerate(cols):
        p = c
        while data[p] != 0xFF:
            top, ln = data[p], data[p + 1]
            img[top:top + ln, x] = list(data[p + 3:p + 3 + ln])
            p += ln + 4
    return img


def main():
    wad = Wad(sys.argv[1])
    mapname = sys.argv[2].upper()
    out = Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)

    mi = wad.find(mapname)
    assert mi >= 0, mapname
    lump = {}
    for k in range(mi + 1, mi + 11):
        lump[wad.lumps[k][0]] = wad.idx(k)

    verts = [struct.unpack_from("<hh", lump["VERTEXES"], i) for i in range(0, len(lump["VERTEXES"]), 4)]
    lines = [struct.unpack_from("<HHHHHHH", lump["LINEDEFS"], i) for i in range(0, len(lump["LINEDEFS"]), 14)]
    sides = []
    for i in range(0, len(lump["SIDEDEFS"]), 30):
        xo, yo = struct.unpack_from("<hh", lump["SIDEDEFS"], i)
        up, lo, mid = (name8(lump["SIDEDEFS"][i + 4 + 8 * k:i + 12 + 8 * k]) for k in range(3))
        sec, = struct.unpack_from("<H", lump["SIDEDEFS"], i + 28)
        sides.append((xo, yo, up, lo, mid, sec))
    secs = []
    for i in range(0, len(lump["SECTORS"]), 26):
        fh, ch = struct.unpack_from("<hh", lump["SECTORS"], i)
        fp, cp = name8(lump["SECTORS"][i + 4:i + 12]), name8(lump["SECTORS"][i + 12:i + 20])
        light, special, tag = struct.unpack_from("<hhh", lump["SECTORS"], i + 20)
        secs.append([fh, ch, fp, cp, light, special, tag])
    segs = [struct.unpack_from("<HHhHHh", lump["SEGS"], i) for i in range(0, len(lump["SEGS"]), 12)]
    ssecs = [struct.unpack_from("<HH", lump["SSECTORS"], i) for i in range(0, len(lump["SSECTORS"]), 4)]
    nodes = [struct.unpack_from("<hhhh8hHH", lump["NODES"], i) for i in range(0, len(lump["NODES"]), 28)]
    things = [struct.unpack_from("<hhhhh", lump["THINGS"], i) for i in range(0, len(lump["THINGS"]), 10)]

    pal = np.frombuffer(wad.get("PLAYPAL")[:768], np.uint8).reshape(256, 3).astype(np.float64)
    cmap = np.frombuffer(wad.get("COLORMAP")[:34 * 256], np.uint8).reshape(34, 256)

    # ---- wall textures
    pn = wad.get("PNAMES")
    pnames = [name8(pn[4 + 8 * i:12 + 8 * i]) for i in range(struct.unpack_from("<I", pn, 0)[0])]
    patches = wad.range(("P_START", "PP_START", "P1_START", "P2_START", "P3_START"), ("P_END", "PP_END", "P1_END", "P2_END", "P3_END"))
    texdefs = {}
    for tl in ("TEXTURE1", "TEXTURE2"):
        t = wad.get(tl)
        if not t:
            continue
        n, = struct.unpack_from("<I", t, 0)
        for o in struct.unpack_from("<%dI" % n, t, 4):
            nm = name8(t[o:o + 8])
            w, h = struct.unpack_from("<HH", t, o + 12)
            np_, = struct.unpack_from("<H", t, o + 20)
            pl = [struct.unpack_from("<hhH", t, o + 22 + 10 * k) for k in range(np_)]
            texdefs[nm] = (w, h, pl)

    pcache = {}

    def compose(nm):
        w, h, pl = texdefs[nm]
        img = np.zeros((h, w), np.int16)
        for ox, oy, pi in pl:
            pnm = pnames[pi]
            if pnm not in pcache:
                pcache[pnm] = read_patch(patches[pnm]) if pnm in patches else np.zeros((1, 1), np.int16)
            p = pcache[pnm]
            ph, pw = p.shape
            for y in range(ph):
                yy = oy + y
                if not 0 <= yy < h:
                    continue
                for x in range(pw):
                    xx = ox + x
                    if 0 <= xx < w and p[y, x] >= 0:
                        img[yy, xx] = p[y, x]
        return img

    # textures and light buckets used by the map
    used = {}   # name -> set(buckets)
    for (v1, v2, fl, sp, tg, r, l) in lines:
        for sd, other in ((r, l), (l, r)):
            if sd == 0xFFFF:
                continue
            xo, yo, up, lo, mid, sec = sides[sd]
            b = bucket_of(secs[sec][4])
            for nm in (up, lo, mid):
                if nm != "-" and nm in texdefs:
                    used.setdefault(nm, set()).add(b)
    texnames = sorted(used)
    teximg = {nm: compose(nm) for nm in texnames}

    flats = wad.range(("F_START", "FF_START"), ("F_END", "FF_END"))
    flatcol = {}
    for s in secs:
        for nm in (s[2], s[3]):
            if nm in flats and nm not in flatcol:
                f = np.frombuffer(flats[nm][:4096], np.uint8)
                flatcol[nm] = f

    # ---- colour: NPAL palettes (one per 8x8 screen tile), each fitted FOR colour pairs.
    # Items = (texture, light bucket) and (flat, light bucket); every item gets one palette.
    import os
    NPAL = int(os.environ.get("DREAD_NPAL", "3"))
    MIXW = float(os.environ.get("DREAD_MIX_PENALTY", "0.08"))
    DAC = np.array([0, 52, 87, 116, 144, 172, 206, 255], float)   # MD DAC levels (approx. measured curve)
    cand_lv = np.array([(r, g, b) for r in range(8) for g in range(8) for b in range(8)])
    cand = DAC[cand_lv]
    lin_c = (cand / 255.0) ** 2.2
    rng = np.random.default_rng(1)

    items = []        # (key, rgb pixels Nx3)
    for nm in texnames:
        img = teximg[nm].astype(np.int64).ravel()
        for b in used[nm]:
            items.append((("t", nm, b), pal[cmap[LIGHT_ROWS[b]][img]]))
    flat_items = set()
    for s_ in secs:
        b = bucket_of(s_[4])
        for nm in (s_[2], s_[3]):
            if nm in flatcol and ("f", nm, b) not in flat_items:
                flat_items.add(("f", nm, b))
                c = pal[cmap[LIGHT_ROWS[b]][flatcol[nm]]].mean(axis=0)
                items.append((("f", nm, b), np.repeat(c[None, :], 400, axis=0)))
    sky_rgb = pal[compose("SKY1").ravel()].mean(0) if "SKY1" in texdefs else np.array([80., 80., 120.])
    items.append((("s",), np.repeat(sky_rgb[None, :], 400, axis=0)))

    def summarize(X, cap):
        q = np.round(X / 8).astype(np.int64)
        key = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
        uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        U = np.zeros((len(uk), 3)); np.add.at(U, inv, X); U /= cnt[:, None]
        w = np.sqrt(cnt)
        if len(U) > cap:
            k = np.argsort(-w)[:cap]; U, w = U[k], w[k]
        return U, w

    def fit_palette(U2, w2):
        def mixd(ia, ib):
            m = ((lin_c[ia] + lin_c[ib]) / 2) ** (1 / 2.2) * 255.0
            sp = np.sqrt(((cand[ia] - cand[ib]) ** 2).sum(-1))
            return np.sqrt(((U2[:, None, :] - m[None]) ** 2).sum(-1)) + MIXW * sp[None]
        chosen = [0]
        err = mixd(np.array([0]), np.array([0]))[:, 0]
        for step in range(15):
            best = None
            for c in range(512):
                if c in chosen: continue
                ia = np.array(chosen + [c]); ib = np.full(len(ia), c)
                e = np.minimum(err, mixd(ia, ib).min(1))
                tot = (e * w2).sum()
                if best is None or tot < best[0]: best = (tot, c, e)
            chosen.append(best[1]); err = best[2]
        def total(ch):
            ch = np.array(ch); ia, ib = np.triu_indices(len(ch))
            return (mixd(ch[ia], ch[ib]).min(1) * w2).sum()
        cur = total(chosen)
        for it in range(2):
            improved = False
            for i in range(1, 16):
                lv = cand_lv[chosen[i]]
                for d in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1),(1,1,1),(-1,-1,-1)]:
                    nl = np.clip(lv + d, 0, 7); nc = int(nl[0] * 64 + nl[1] * 8 + nl[2])
                    if nc in chosen: continue
                    trial = chosen[:i] + [nc] + chosen[i + 1:]
                    t = total(trial)
                    if t < cur: cur, chosen, improved = t, trial, True; lv = nl
            if not improved: break
        # luminance order: index i means a similar brightness in every palette, so a tile shown with
        # the "wrong" palette (two families meeting in one 8x8 tile) keeps its shading
        lum = (cand[chosen] * [0.3, 0.59, 0.11]).sum(1)
        chosen = [chosen[i] for i in np.argsort(lum, kind="stable")]
        return chosen, cur / w2.sum()

    class Pal:
        def __init__(self, chosen):
            self.lv = [tuple(int(v) for v in cand_lv[c]) for c in chosen]
            self.rgb = cand[chosen]
            lin = (self.rgb / 255.0) ** 2.2
            self.pairs = [(x, y) for x in range(16) for y in range(x, 16)]
            self.mix = np.array([((lin[x] + lin[y]) / 2) ** (1 / 2.2) * 255.0 for x, y in self.pairs])
            self.spread = np.array([np.sqrt(((self.rgb[x] - self.rgb[y]) ** 2).sum()) for x, y in self.pairs])
        def cost(self, X):          # per-pixel error with the best pair
            d = np.sqrt(((X[:, None, :] - self.mix[None]) ** 2).sum(-1)) + MIXW * self.spread[None]
            return d.min(1)
        def pair(self, rgb):
            d = np.sqrt(((self.mix - rgb) ** 2).sum(-1)) + MIXW * self.spread
            x, y = self.pairs[int(d.argmin())]
            if self.rgb[x].sum() > self.rgb[y].sum(): x, y = y, x
            return x, y
        def byte(self, rgb):
            x, y = self.pair(rgb); return (x << 4) | y

    # initial grouping: k-means on the items' mean colour (chroma direction), then refine by fit error
    means = np.array([X.mean(0) for _, X in items])
    sizes = np.array([len(X) for _, X in items], float)
    feat = means / (means.sum(1, keepdims=True) + 1)      # chromaticity
    C = feat[rng.choice(len(feat), NPAL, replace=False)]
    for _ in range(20):
        asg = ((feat[:, None] - C[None]) ** 2).sum(-1).argmin(1)
        for k in range(NPAL):
            if (asg == k).any(): C[k] = (feat[asg == k] * sizes[asg == k, None]).sum(0) / sizes[asg == k].sum()
    pals = []
    for rnd in range(int(os.environ.get("DREAD_PAL_ROUNDS", "2"))):
        pals = []
        for k in range(NPAL):
            sel = [X for (it, X), g in zip(items, asg) if g == k]
            if not sel: sel = [items[0][1]]
            U2, w2 = summarize(np.concatenate(sel), 1500)
            ch, e = fit_palette(U2, w2)
            pals.append(Pal(ch))
            print("palette %d: %d items, mean pair error %.1f" % (k, len(sel), e))
        # reassign every item to the palette that renders it best
        sub = [X if len(X) <= 600 else X[rng.choice(len(X), 600, replace=False)] for _, X in items]
        asg = np.array([int(np.argmin([pl.cost(Xs).mean() for pl in pals])) for Xs in sub])
    pal_of = {it: int(g) for (it, _), g in zip(items, asg)}

    lut = {}
    def lut_for(b, k):
        if (b, k) not in lut:
            pl = pals[k]
            lut[(b, k)] = [pl.pair(pal[cmap[LIGHT_ROWS[b]][i]]) for i in range(256)]
        return lut[(b, k)]

    skypal = pal_of[("s",)]
    skycol = pals[skypal].byte(sky_rgb)

    # ---- emit textures
    texmeta = []     # (wshift, hshift, realh, realw, [offset per bucket], [palette per bucket])
    blob = bytearray()
    for nm in texnames:
        img = teximg[nm]
        h, w = img.shape
        hw = max(1, w // 2)
        wsh = max(0, math.ceil(math.log2(hw)))
        hsh = max(0, math.ceil(math.log2(h)))
        W2, H2 = 1 << wsh, 1 << hsh
        offs, pids = [], []
        for b in range(len(LIGHT_ROWS)):
            if b not in used[nm]:
                offs.append(None); pids.append(None)
                continue
            k = pal_of[("t", nm, b)]
            L = lut_for(b, k)
            col = bytearray()
            for u in range(W2):
                sx = (u % hw) * 2
                one = bytearray()
                for v in range(H2):
                    pa, pb = L[img[v % h, sx]]
                    one.append(pa << 4 | pb)   # same order on every row: clean screen-aligned vertical lines
                col += one + one          # stored twice: the renderer skips the wrap mask
            offs.append(len(blob)); pids.append(k)
            blob += col
        for b in range(len(offs)):
            if offs[b] is None:
                nb = min(used[nm], key=lambda x: abs(x - b))
                offs[b] = offs[nb]; pids[b] = pids[nb]
        texmeta.append((wsh, hsh, h, w, offs, pids))
    tid = {nm: i for i, nm in enumerate(texnames)}

    # ---- map structures
    def sec_of_side(sd):
        return sides[sd][5] if sd != 0xFFFF else 0xFF

    seg_rows = []
    for (v1, v2, ang, ld, side, off) in segs:
        lv1, lv2, fl, sp, tg, r, l = lines[ld]
        fsd, bsd = (r, l) if side == 0 else (l, r)
        xo, yo, up, lo, mid, fs = sides[fsd]
        bs = sec_of_side(bsd) if (fl & 4) else 0xFF
        t = lambda nm: tid.get(nm, 255)
        flags = (1 if fl & 8 else 0) | (2 if fl & 16 else 0) | (4 if bs != 0xFF else 0)
        ln = int(round(math.hypot(verts[v2][0] - verts[v1][0], verts[v2][1] - verts[v1][1])))
        seg_rows.append((v1, v2, fs, bs, t(mid), t(up), t(lo), flags, off + xo, yo, ld, ln))

    sec_rows = []
    for (fh, ch, fp, cp, light, special, tag) in secs:
        b = bucket_of(light)
        def fc(nm):
            if nm not in flatcol or ("f", nm, b) not in pal_of:
                return skycol, skypal
            k = pal_of[("f", nm, b)]
            return pals[k].byte(pal[cmap[LIGHT_ROWS[b]][flatcol[nm]]].mean(axis=0)), k
        sky = 1 if cp.startswith("F_SKY") else 0
        fcol, fpal = fc(fp)
        ccol, cpal = (skycol, skypal) if sky else fc(cp)
        sec_rows.append((fh, ch, fcol, ccol, b, sky, fpal, cpal))
    md = pals[0].lv
    ss_sec = []
    for (cnt, first) in ssecs:
        ss_sec.append(seg_rows[first][2])

    start = next((t for t in things if t[3] == 1), things[0])

    # ---- write C
    H = []
    H.append("/* generated by conv.py from %s %s -- do not edit */" % (Path(sys.argv[1]).name, mapname))
    H.append("#include \"mapdata.h\"")
    H.append("const uint16_t md_palette[%d][16] = {%s};" % (NPAL, ",".join("{%s}" % ",".join(
        "0x%03X" % ((c[2] * 2) << 8 | (c[1] * 2) << 4 | (c[0] * 2)) for c in pl.lv) for pl in pals)))
    H.append("const uint8_t pal_rgb_all[%d][16][3] = {%s};" % (NPAL, ",".join("{%s}" % ",".join(
        "{%d,%d,%d}" % tuple(int(DAC[l]) for l in c) for c in pl.lv) for pl in pals)))
    H.append("const uint16_t num_palettes = %d;" % NPAL)
    # remap[A][B]: a pair byte of palette A -> the closest pair byte in palette B. Stored at (byte ^ 0x80)
    # so the 68000 can index it with a sign-extended byte (table base + 128).
    rem = []
    for A in range(NPAL):
        for Bp in range(NPAL):
            t = [0] * 256
            for bt in range(256):
                x, y = bt >> 4, bt & 15
                la, lb = (pals[A].rgb[x] / 255.0) ** 2.2, (pals[A].rgb[y] / 255.0) ** 2.2
                rgb = ((la + lb) / 2) ** (1 / 2.2) * 255.0
                t[bt ^ 0x80] = bt if A == Bp else pals[Bp].byte(rgb)
            rem.append("{%s}" % ",".join(map(str, t)))
    H.append("const uint8_t pal_remap[%d][256] = {%s};" % (NPAL * NPAL, ",".join(rem)))
    H.append("const int16_t map_verts[%d][2] = {%s};" % (len(verts), ",".join("{%d,%d}" % v for v in verts)))
    H.append("const MapSeg map_segs[%d] = {%s};" % (len(seg_rows), ",".join(
        "{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d}" % r for r in seg_rows)))
    H.append("const MapSub map_subs[%d] = {%s};" % (len(ssecs), ",".join(
        "{%d,%d,%d}" % (first, cnt, ss_sec[i]) for i, (cnt, first) in enumerate(ssecs))))
    H.append("const MapNode map_nodes[%d] = {%s};" % (len(nodes), ",".join(
        "{%d,%d,%d,%d,{{%d,%d,%d,%d},{%d,%d,%d,%d}},{%d,%d}}" % n for n in nodes)))
    H.append("const MapSector map_sectors_init[%d] = {%s};" % (len(sec_rows), ",".join(
        "{%d,%d,%d,%d,%d,%d,%d,%d}" % r for r in sec_rows)))
    H.append("const MapLine map_lines[%d] = {%s};" % (len(lines), ",".join(
        "{%d,%d,%d,%d,%d,%d,%d}" % (l[0], l[1], l[2], sec_of_side(l[5]), sec_of_side(l[6]), l[3], l[4]) for l in lines)))
    # doors: sectors behind manual door lines, plus sectors tagged by switch/use door lines.
    # open height = lowest neighbouring ceiling - 4 (as in Doom)
    MANUAL = {1, 26, 27, 28, 31, 32, 33, 34, 117, 118}
    TAGGED = {29, 50, 63, 103, 111, 112, 113, 114, 115, 61, 42, 116}
    neigh = {}
    for (v1, v2, fl, sp, tg, r, l) in lines:
        if r != 0xFFFF and l != 0xFFFF:
            a, b = sides[r][5], sides[l][5]
            neigh.setdefault(a, set()).add(b); neigh.setdefault(b, set()).add(a)
    doors = set()
    for (v1, v2, fl, sp, tg, r, l) in lines:
        if sp in MANUAL and l != 0xFFFF: doors.add(sides[l][5])
        if sp in TAGGED and tg:
            for i, sc in enumerate(secs):
                if sc[6] == tg: doors.add(i)
    door_rows = []
    for d in sorted(doors):
        ns = [secs[n][1] for n in neigh.get(d, ()) if n != d]
        top = (min(ns) - 4) if ns else secs[d][1] + 72
        if top > secs[d][0]: door_rows.append((d, top))
    H.append("const MapDoor map_doors[%d] = {%s};" % (max(1, len(door_rows)), ",".join("{%d,%d}" % r for r in door_rows) or "{0,0}"))
    H.append("const uint16_t map_ndoors = %d;" % len(door_rows))
    H.append("const int16_t map_sector_tag[%d] = {%s};" % (len(secs), ",".join(str(sc[6]) for sc in secs)))
    H.append("const uint8_t tex_blob[%d] = {%s};" % (len(blob), ",".join(str(x) for x in blob)))
    # same texels as words (b, b): column-doubled modes write 4 pixels per texel with one move.w
    H.append("const uint16_t tex_blob_w[%d] = {%s};" % (len(blob), ",".join(str(x * 257) for x in blob)))
    H.append("const MapTex map_tex[%d] = {%s};" % (max(1, len(texmeta)), ",".join(
        "{%d,%d,%d,%d,{%s},{%s}}" % (m[0], m[1], m[2], m[3], ",".join(str(o) for o in m[4]), ",".join(str(x) for x in m[5])) for m in texmeta) or "{0}"))
    H.append("const int16_t sintab[1024] = {%s};" % ",".join(str(int(round(16384 * math.sin(i * 2 * math.pi / 1024)))) for i in range(1024)))
    H.append("const int16_t map_start[3] = {%d,%d,%d};" % (start[0], start[1], start[2]))
    H.append("const uint16_t map_counts[6] = {%d,%d,%d,%d,%d,%d};" % (
        len(verts), len(seg_rows), len(ssecs), len(nodes), len(sec_rows), len(lines)))
    (out / "mapdata.c").write_text("\n".join(H) + "\n")

    print("map %s: %d verts %d segs %d subsectors %d nodes %d sectors %d lines; %d textures, texture blob %d bytes; sky %d"
          % (mapname, len(verts), len(seg_rows), len(ssecs), len(nodes), len(sec_rows), len(lines), len(texnames), len(blob), skycol))
    for k, pl in enumerate(pals): print("palette", k, pl.lv)


if __name__ == "__main__":
    main()
