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

    # ---- palette fit: sample all used pixels (Doom index after light) -> RGB
    samples = []
    for nm in texnames:
        img = teximg[nm].astype(np.int64)
        for b in used[nm]:
            samples.append(pal[cmap[LIGHT_ROWS[b]][img.ravel()]])
    for s in secs:
        b = bucket_of(s[4])
        for nm in (s[2], s[3]):
            if nm in flatcol:
                c = pal[cmap[LIGHT_ROWS[b]][flatcol[nm]]].mean(axis=0)
                samples.append(np.repeat(c[None, :], 1500, axis=0))
    X = np.concatenate(samples)
    rng = np.random.default_rng(1)
    if len(X) > 60000:
        X = X[rng.choice(len(X), 60000, replace=False)]
    K = 15
    C = X[rng.choice(len(X), K, replace=False)]
    for _ in range(25):
        d = ((X[:, None, :] - C[None]) ** 2).sum(-1)
        a = d.argmin(1)
        for k in range(K):
            m = X[a == k]
            if len(m):
                C[k] = m.mean(0)
    # MD 9-bit colour (levels 0..7 per channel, DAC ~ 0..252)
    mdlev = lambda v: int(max(0, min(7, round(v / 36.43))))
    md = [(0, 0, 0)] + [(mdlev(c[0]), mdlev(c[1]), mdlev(c[2])) for c in C]
    mdrgb = np.array([[l * 36.43 for l in c] for c in md])

    def nearest(rgb):
        return int(((mdrgb - rgb) ** 2).sum(-1).argmin())

    lut = np.zeros((len(LIGHT_ROWS), 256), np.uint8)
    for b, row in enumerate(LIGHT_ROWS):
        for i in range(256):
            lut[b, i] = nearest(pal[cmap[row][i]])

    # sky colour
    sky_rgb = None
    if "SKY1" in texdefs:
        sky_rgb = pal[compose("SKY1").ravel()].mean(0)
    skycol = nearest(sky_rgb) if sky_rgb is not None else 1

    # ---- emit textures
    texc = []
    texmeta = []     # (wshift, hshift, realh, [offset per bucket])
    blob = bytearray()
    for nm in texnames:
        img = teximg[nm]
        h, w = img.shape
        hw = max(1, w // 2)
        wsh = max(0, math.ceil(math.log2(hw)))
        hsh = max(0, math.ceil(math.log2(h)))
        W2, H2 = 1 << wsh, 1 << hsh
        offs = []
        for b in range(len(LIGHT_ROWS)):
            if b not in used[nm]:
                offs.append(None)
                continue
            col = bytearray()
            for u in range(W2):
                sx = (u % hw) * 2
                for v in range(H2):
                    c = int(lut[b, img[v % h, sx]])
                    col.append(c | (c << 4))
            offs.append(len(blob))
            blob += col
        # fill missing buckets with the nearest used one
        for b in range(len(offs)):
            if offs[b] is None:
                nb = min(used[nm], key=lambda x: abs(x - b))
                offs[b] = offs[nb]
        texmeta.append((wsh, hsh, h, w, offs))
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
            if nm not in flatcol:
                return skycol
            return nearest(pal[cmap[LIGHT_ROWS[b]][flatcol[nm]]].mean(axis=0))
        sky = 1 if cp.startswith("F_SKY") else 0
        sec_rows.append((fh, ch, fc(fp), skycol if sky else fc(cp), b, sky))

    ss_sec = []
    for (cnt, first) in ssecs:
        ss_sec.append(seg_rows[first][2])

    start = next((t for t in things if t[3] == 1), things[0])

    # ---- write C
    H = []
    H.append("/* generated by conv.py from %s %s -- do not edit */" % (Path(sys.argv[1]).name, mapname))
    H.append("#include \"mapdata.h\"")
    H.append("const uint16_t md_palette[16] = {%s};" % ",".join(
        "0x%03X" % ((c[2] * 2) << 8 | (c[1] * 2) << 4 | (c[0] * 2)) for c in md))
    H.append("const uint8_t pal_rgb[16][3] = {%s};" % ",".join("{%d,%d,%d}" % tuple(int(l * 36.43) for l in c) for c in md))
    H.append("const int16_t map_verts[%d][2] = {%s};" % (len(verts), ",".join("{%d,%d}" % v for v in verts)))
    H.append("const MapSeg map_segs[%d] = {%s};" % (len(seg_rows), ",".join(
        "{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d}" % r for r in seg_rows)))
    H.append("const MapSub map_subs[%d] = {%s};" % (len(ssecs), ",".join(
        "{%d,%d,%d}" % (first, cnt, ss_sec[i]) for i, (cnt, first) in enumerate(ssecs))))
    H.append("const MapNode map_nodes[%d] = {%s};" % (len(nodes), ",".join(
        "{%d,%d,%d,%d,{{%d,%d,%d,%d},{%d,%d,%d,%d}},{%d,%d}}" % n for n in nodes)))
    H.append("const MapSector map_sectors_init[%d] = {%s};" % (len(sec_rows), ",".join(
        "{%d,%d,%d,%d,%d,%d}" % r for r in sec_rows)))
    H.append("const MapLine map_lines[%d] = {%s};" % (len(lines), ",".join(
        "{%d,%d,%d,%d,%d}" % (l[0], l[1], l[2], sec_of_side(l[5]), sec_of_side(l[6])) for l in lines)))
    H.append("const uint8_t tex_blob[%d] = {%s};" % (len(blob), ",".join(str(x) for x in blob)))
    H.append("const MapTex map_tex[%d] = {%s};" % (max(1, len(texmeta)), ",".join(
        "{%d,%d,%d,%d,{%s}}" % (m[0], m[1], m[2], m[3], ",".join(str(o) for o in m[4])) for m in texmeta) or "{0}"))
    H.append("const int16_t sintab[1024] = {%s};" % ",".join(str(int(round(16384 * math.sin(i * 2 * math.pi / 1024)))) for i in range(1024)))
    H.append("const int16_t map_start[3] = {%d,%d,%d};" % (start[0], start[1], start[2]))
    H.append("const uint16_t map_counts[6] = {%d,%d,%d,%d,%d,%d};" % (
        len(verts), len(seg_rows), len(ssecs), len(nodes), len(sec_rows), len(lines)))
    (out / "mapdata.c").write_text("\n".join(H) + "\n")

    print("map %s: %d verts %d segs %d subsectors %d nodes %d sectors %d lines; %d textures, texture blob %d bytes; sky %d"
          % (mapname, len(verts), len(seg_rows), len(ssecs), len(nodes), len(sec_rows), len(lines), len(texnames), len(blob), skycol))
    print("palette", md)


if __name__ == "__main__":
    main()
