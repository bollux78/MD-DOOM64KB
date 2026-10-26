#!/usr/bin/env python3
"""Recreate the Doom status bar for the Mega Drive from the original IWAD (not committed: read at build time).

Reads the status-bar patches of a Doom IWAD (STBAR, STTNUM*, STYSNUM*, STGNUM*, STKEYS*, STF* faces), resamples them onto the 8x8 tile
grid of the VDP, quantises everything to ONE 16-colour CRAM line (index 0 = black) and writes a C header with ROM tables:

    hud_pal[16]            CRAM words (0x0BGR) for palette line 3
    hud_tiles[N][8]        static tiles: background, big digits (8x16 as top/bottom tiles), small digits, keys, blanks
    hud_bgmap[4][32]       background tile ids (index into hud_tiles) of the 32x4-cell bar
    hud_faces[42][12][8]   face frames, 3 x 4 tiles each, uploaded to a 12-tile VRAM slot when the face changes

The bar is a recreation, not a copy: STBAR is squeezed from 320 to 256 pixels (0.8 horizontally) so it fits both the H32 and the
H40 screen, numbers and faces are separate tile-aligned widgets, and the 15 colours are chosen by k-means over all the artwork.
Usage: gen_hud_wad.py --wad doom1.wad --out src/hud_wad_assets.h [--preview hud-preview.png]
"""
import argparse, struct, sys, zlib

COLS, ROWS = 32, 4
# ---- widget layout (tile columns/rows of the 32x4 bar); shared with src/hud_wad_logic.h through the generated header -------------
LAYOUT = dict(
    AMMO_C=1, AMMO_R=0,          # 3 big digits, rows 0..1
    HEALTH_C=5, HEALTH_R=0,      # 3 big digits + percent sign
    ARMOR_C=18, ARMOR_R=0,       # 3 big digits + percent sign
    ARMS_C=10, ARMS_R=0,         # 3x2 small digits (weapons 2..7)
    FACE_C=14, FACE_R=0,         # 3 x 4 tiles
    KEYS_C=24, KEYS_R=0,         # 3 stacked tiles
    TABLE_C=26, TABLE_R=0,       # 4 rows: ammo current (3 digits) + maximum (3 digits)
)
FACE_NAMES = []
for p in range(5):
    FACE_NAMES += ["STFST%d0" % p, "STFST%d1" % p, "STFST%d2" % p, "STFTR%d0" % p, "STFTL%d0" % p,
                   "STFOUCH%d" % p, "STFEVL%d" % p, "STFKILL%d" % p]
FACE_NAMES += ["STFGOD0", "STFDEAD0"]


class WadError(Exception):
    pass


def read_iwad(data):
    if data[:4] not in (b"IWAD", b"PWAD"):
        raise WadError("not an IWAD/PWAD")
    n, ofs = struct.unpack_from("<ii", data, 4)
    lumps = {}
    for i in range(n):
        pos, size, name = struct.unpack_from("<ii8s", data, ofs + 16 * i)
        lumps[name.split(b"\0")[0].decode("ascii", "replace").upper()] = data[pos:pos + size]
    return lumps


def decode_patch(b):
    """Doom picture format -> (w, h, rows) with rows[y][x] = palette index or -1 (transparent)."""
    w, h, lo, to = struct.unpack_from("<hhhh", b, 0)
    if not (0 < w <= 512 and 0 < h <= 256):
        raise WadError("implausible patch size %dx%d" % (w, h))
    rows = [[-1] * w for _ in range(h)]
    for x in range(w):
        o = struct.unpack_from("<i", b, 8 + 4 * x)[0]
        while True:
            top = b[o]
            if top == 0xFF:
                break
            ln = b[o + 1]
            for i in range(ln):
                y = top + i
                if y < h:
                    rows[y][x] = b[o + 3 + i]
            o += ln + 4
    return w, h, rows


def encode_patch(rows):
    """Inverse of decode_patch (used by the tests to build a synthetic IWAD)."""
    h, w = len(rows), len(rows[0])
    cols, body = [], b""
    for x in range(w):
        cols.append(8 + 4 * w + len(body))
        y = 0
        while y < h:
            if rows[y][x] < 0:
                y += 1
                continue
            y2 = y
            while y2 < h and rows[y2][x] >= 0:
                y2 += 1
            body += bytes([y, y2 - y, 0]) + bytes(rows[yy][x] for yy in range(y, y2)) + b"\0"
            y = y2
        body += b"\xff"
    return struct.pack("<hhhh", w, h, 0, 0) + b"".join(struct.pack("<i", c) for c in cols) + body


def make_iwad(lumps):
    """lumps: list of (name, bytes) -> IWAD bytes."""
    out, dirs = b"", []
    base = 12
    for name, data in lumps:
        dirs.append(struct.pack("<ii8s", base + len(out), len(data), name.encode().ljust(8, b"\0")))
        out += data
    return b"IWAD" + struct.pack("<ii", len(lumps), base + len(out)) + out + b"".join(dirs)


# ---- image helpers: images are lists of rows of (r, g, b) or None (transparent) ---------------------------------------------------
def patch_rgb(rows, pal):
    return [[None if v < 0 else pal[v] for v in r] for r in rows]


def box_resample(img, dw, dh, bg):
    """Area-average resample of an image with transparency onto bg (an RGB triple) -> RGB image."""
    sh, sw = len(img), len(img[0])
    out = []
    for dy in range(dh):
        y0, y1 = dy * sh / dh, (dy + 1) * sh / dh
        row = []
        for dx in range(dw):
            x0, x1 = dx * sw / dw, (dx + 1) * sw / dw
            acc, wsum, cov = [0.0, 0.0, 0.0], 0.0, 0.0
            yy = int(y0)
            while yy < y1 and yy < sh:
                wy = min(y1, yy + 1) - max(y0, yy)
                xx = int(x0)
                while xx < x1 and xx < sw:
                    wx = min(x1, xx + 1) - max(x0, xx)
                    wgt = wx * wy
                    px = img[yy][xx]
                    wsum += wgt
                    if px is not None:
                        cov += wgt
                        for k in range(3):
                            acc[k] += px[k] * wgt
                    xx += 1
                yy += 1
            if wsum <= 0:
                row.append(bg)
                continue
            a = cov / wsum
            if cov > 0:
                col = [acc[k] / cov for k in range(3)]
            else:
                col = list(bg)
            row.append(tuple(int(round(col[k] * a + bg[k] * (1 - a))) for k in range(3)))
        out.append(row)
    return out


def paste(dst, src, x0, y0):
    for y, r in enumerate(src):
        for x, v in enumerate(r):
            if 0 <= y0 + y < len(dst) and 0 <= x0 + x < len(dst[0]):
                dst[y0 + y][x0 + x] = v


def solid(w, h, c):
    return [[c] * w for _ in range(h)]


def median_color(img, x0, y0, x1, y1):
    vals = [[], [], []]
    for y in range(y0, min(y1, len(img))):
        for x in range(x0, min(x1, len(img[0]))):
            for k in range(3):
                vals[k].append(img[y][x][k])
    if not vals[0]:
        return (0, 0, 0)
    return tuple(sorted(v)[len(v) // 2] for v in vals)


def tile_of(img, tx, ty):
    return tuple(tuple(img[ty * 8 + y][tx * 8 + x] for x in range(8)) for y in range(8))


# ---- asset construction -----------------------------------------------------------------------------------------------------------
def build_images(lumps):
    pp = lumps.get("PLAYPAL")
    if pp is None or len(pp) < 768:
        raise WadError("PLAYPAL missing")
    pal = [tuple(pp[3 * i:3 * i + 3]) for i in range(256)]
    need = ["STBAR", "STTPRCNT"] + ["STTNUM%d" % i for i in range(10)] + ["STYSNUM%d" % i for i in range(10)] + \
           ["STGNUM%d" % i for i in range(10)] + ["STKEYS0", "STKEYS1", "STKEYS2"] + FACE_NAMES
    missing = [n for n in need if n not in lumps]
    if missing:
        raise WadError("missing lumps: " + ", ".join(missing))
    P = {n: decode_patch(lumps[n]) for n in need}
    rgb = lambda n: patch_rgb(P[n][2], pal)

    stbar = rgb("STBAR")
    sw, sh = P["STBAR"][0], P["STBAR"][1]
    # 1. the background: STBAR squeezed to 256 x 32 (4/5 horizontally), vertically cropped/padded to 32.
    black = (0, 0, 0)
    bar = box_resample([[px if px is not None else black for px in r] for r in stbar], COLS * 8, ROWS * 8, black)
    # panel colours behind the widgets, sampled from the squeezed bar so the tiles blend in
    L = LAYOUT
    panel_big = median_color(bar, L["HEALTH_C"] * 8, 0, (L["HEALTH_C"] + 3) * 8, 16)
    panel_small = median_color(bar, L["ARMS_C"] * 8, 0, (L["ARMS_C"] + 3) * 8, 16)
    panel_face = median_color(bar, L["FACE_C"] * 8, 0, (L["FACE_C"] + 3) * 8, 32)
    panel_key = median_color(bar, L["KEYS_C"] * 8, 0, (L["KEYS_C"] + 1) * 8, 24)
    # 2. widget glyph images
    def glyph(name, dw, dh, bg):
        return box_resample(rgb(name), dw, dh, bg)
    big = {}
    for d in range(10):
        big[d] = glyph("STTNUM%d" % d, 8, 16, panel_big)
    big["%"] = glyph("STTPRCNT", 8, 16, panel_big)
    big[" "] = solid(8, 16, panel_big)
    def small(name):
        g = rgb(name)
        w, h = P[name][0], P[name][1]
        img = solid(8, 8, panel_small)
        ox, oy = (8 - w) // 2, (8 - h) // 2
        for y in range(h):
            for x in range(w):
                if g[y][x] is not None and 0 <= ox + x < 8 and 0 <= oy + y < 8:
                    img[oy + y][ox + x] = g[y][x]
        return img
    ysm = {d: small("STYSNUM%d" % d) for d in range(10)}
    gsm = {d: small("STGNUM%d" % d) for d in range(10)}
    ysm[" "] = solid(8, 8, panel_small)
    keys = []
    for k in range(3):
        g = rgb("STKEYS%d" % k)
        w, h = P["STKEYS%d" % k][0], P["STKEYS%d" % k][1]
        img = solid(8, 8, panel_key)
        for y in range(min(h, 8)):
            for x in range(min(w, 8)):
                if g[y][x] is not None:
                    img[y][x] = g[y][x]
        keys.append(img)
    keys.append(solid(8, 8, panel_key))     # no key
    faces = []
    for n in FACE_NAMES:
        g = rgb(n)
        w, h = P[n][0], P[n][1]
        img = solid(24, 32, panel_face)
        ox, oy = (24 - w) // 2, (32 - h) // 2
        for y in range(h):
            for x in range(w):
                if g[y][x] is not None and 0 <= ox + x < 24 and 0 <= oy + y < 32:
                    img[oy + y][ox + x] = g[y][x]
        faces.append(img)
    return dict(bar=bar, big=big, ysm=ysm, gsm=gsm, keys=keys, faces=faces, panel_small=panel_small)


def quantise_palette(colours, k=15, iters=12):
    """colours: dict RGB -> weight. Returns 15 centres (RGB, 3 bits/channel precision as the MD has)."""
    def md(c):   # snap to the 8 levels per channel of the 9-bit Mega Drive palette (and back to 8 bits)
        return tuple(min(255, (c[i] >> 5) * 255 // 7) for i in range(3))
    snapped = {}
    for c, w in colours.items():
        m = md(c)
        snapped[m] = snapped.get(m, 0) + w
    items = sorted(snapped.items(), key=lambda kv: (-kv[1], kv[0]))
    dist = lambda a, b: 2 * (a[0] - b[0]) ** 2 + 4 * (a[1] - b[1]) ** 2 + 3 * (a[2] - b[2]) ** 2
    centres = []
    # farthest-point seeding weighted by frequency (deterministic)
    centres.append(items[0][0])
    while len(centres) < min(k, len(items)):
        best, bs = None, -1
        for c, w in items:
            d = min(dist(c, x) for x in centres)
            s = d * (w ** 0.5)
            if s > bs or (s == bs and c < best):
                best, bs = c, s
        centres.append(best)
    for _ in range(iters):
        groups = [[0.0, 0.0, 0.0, 0.0] for _ in centres]
        for c, w in items:
            j = min(range(len(centres)), key=lambda i: (dist(c, centres[i]), i))
            for t in range(3):
                groups[j][t] += c[t] * w
            groups[j][3] += w
        new = []
        for j, g in enumerate(groups):
            new.append(md(tuple(int(g[t] / g[3]) for t in range(3))) if g[3] else centres[j])
        if new == centres:
            break
        centres = new
    return centres


def md_word(c):
    return ((c[2] >> 5) << 9) | ((c[1] >> 5) << 5) | ((c[0] >> 5) << 1)


def build_assets(lumps):
    im = build_images(lumps)
    L = LAYOUT
    # static background tile cells: the squeezed STBAR, with every dynamic cell replaced by the blank panel tile of its widget
    bar = [row[:] for row in im["bar"]]
    # collect every tile (as RGB) in a stable order
    tiles_rgb = []            # list of 8x8 RGB tiles
    index = {}
    def add(t):
        key = t
        if key not in index:
            index[key] = len(tiles_rgb)
            tiles_rgb.append(t)
        return index[key]
    def tile_img(img8, ty=0):
        return tuple(tuple(img8[y + ty * 8][x] for x in range(8)) for y in range(8))
    ids = {}
    # dynamic widgets first (stable ids), then the background
    ids["big_top"] = [add(tile_img(im["big"][d], 0)) for d in range(10)]
    ids["big_bot"] = [add(tile_img(im["big"][d], 1)) for d in range(10)]
    ids["pct_top"], ids["pct_bot"] = add(tile_img(im["big"]["%"], 0)), add(tile_img(im["big"]["%"], 1))
    ids["blank_top"], ids["blank_bot"] = add(tile_img(im["big"][" "], 0)), add(tile_img(im["big"][" "], 1))
    ids["ysm"] = [add(tile_img(im["ysm"][d])) for d in range(10)]
    ids["gsm"] = [add(tile_img(im["gsm"][d])) for d in range(10)]
    ids["blank_small"] = add(tile_img(im["ysm"][" "]))
    ids["keys"] = [add(tile_img(k)) for k in im["keys"]]
    n_dynamic = len(tiles_rgb)
    bg_ids = [[0] * COLS for _ in range(ROWS)]
    dyn_cells = set()
    for i in range(3):
        for rr in range(2):
            for c0 in (L["AMMO_C"], L["HEALTH_C"], L["ARMOR_C"]):
                dyn_cells.add((c0 + i, L["AMMO_R"] + rr))
    for rr in range(2):
        dyn_cells.add((L["HEALTH_C"] + 3, rr)); dyn_cells.add((L["ARMOR_C"] + 3, rr))
    for i in range(3):
        for rr in range(2):
            dyn_cells.add((L["ARMS_C"] + i, L["ARMS_R"] + rr))
    for i in range(3):
        for rr in range(4):
            dyn_cells.add((L["FACE_C"] + i, L["FACE_R"] + rr))
    for rr in range(3):
        dyn_cells.add((L["KEYS_C"], L["KEYS_R"] + rr))
    for rr in range(4):
        for i in range(6):
            dyn_cells.add((L["TABLE_C"] + i, L["TABLE_R"] + rr))
    for ty in range(ROWS):
        for tx in range(COLS):
            if (tx, ty) in dyn_cells:
                # blank background behind the widget: big-number panel for big areas, small panel for the rest
                if (tx, ty) in [(c0 + i, rr) for c0 in (L["AMMO_C"], L["HEALTH_C"], L["ARMOR_C"]) for i in range(4) for rr in range(2)]:
                    bg_ids[ty][tx] = ids["blank_top"] if ty == 0 else ids["blank_bot"]
                else:
                    bg_ids[ty][tx] = ids["blank_small"]
            else:
                bg_ids[ty][tx] = add(tile_of(bar, tx, ty))
    # face frames as tiles (3 x 4 each); not part of the static table
    face_tiles = []
    for img in im["faces"]:
        face_tiles.append([tile_of(img, tx, ty) for ty in range(4) for tx in range(3)])
    # palette from all colours used
    hist = {}
    for t in tiles_rgb:
        for r in t:
            for c in r:
                hist[c] = hist.get(c, 0) + 1
    for ft in face_tiles:
        for t in ft:
            for r in t:
                for c in r:
                    hist[c] = hist.get(c, 0) + 1
    centres = quantise_palette(hist)
    palette = [(0, 0, 0)] + centres
    while len(palette) < 16:
        palette.append((0, 0, 0))
    dist = lambda a, b: 2 * (a[0] - b[0]) ** 2 + 4 * (a[1] - b[1]) ** 2 + 3 * (a[2] - b[2]) ** 2
    cache = {}
    def nearest(c):
        if c not in cache:
            cache[c] = min(range(16), key=lambda i: (dist(c, palette[i]), i))
        return cache[c]
    def pack(t):
        return [sum(nearest(t[y][x]) << (28 - 4 * x) for x in range(8)) for y in range(8)]
    return dict(palette=palette, tiles=[pack(t) for t in tiles_rgb], tiles_rgb=tiles_rgb, ids=ids, bgmap=bg_ids,
                faces=[[pack(t) for t in ft] for ft in face_tiles], n_dynamic=n_dynamic)


def emit_header(a):
    L = LAYOUT
    o = ["/* Generated by scripts/lab/gen_hud_wad.py from the user's IWAD. Do not commit. */",
         "#ifndef HUD_WAD_ASSETS_H", "#define HUD_WAD_ASSETS_H", "#include <stdint.h>", ""]
    o.append("#define HUDW_COLS %d\n#define HUDW_ROWS %d" % (COLS, ROWS))
    for k, v in L.items():
        o.append("#define HUDW_%s %d" % (k, v))
    ids = a["ids"]
    o.append("#define HUDW_NTILES %d" % len(a["tiles"]))
    o.append("#define HUDW_NFACES %d" % len(a["faces"]))
    o.append("#define HUDW_BLANK_TOP %d\n#define HUDW_BLANK_BOT %d\n#define HUDW_BLANK_SMALL %d" % (ids["blank_top"], ids["blank_bot"], ids["blank_small"]))
    o.append("#define HUDW_PCT_TOP %d\n#define HUDW_PCT_BOT %d" % (ids["pct_top"], ids["pct_bot"]))
    o.append("static const uint8_t hudw_big_top[10] = {%s};" % ",".join(map(str, ids["big_top"])))
    o.append("static const uint8_t hudw_big_bot[10] = {%s};" % ",".join(map(str, ids["big_bot"])))
    o.append("static const uint8_t hudw_ysm[10] = {%s};" % ",".join(map(str, ids["ysm"])))
    o.append("static const uint8_t hudw_gsm[10] = {%s};" % ",".join(map(str, ids["gsm"])))
    o.append("static const uint8_t hudw_keys[4] = {%s};" % ",".join(map(str, ids["keys"])))
    o.append("static const uint16_t hudw_pal[16] = {%s};" % ",".join("0x%04X" % md_word(c) for c in a["palette"]))
    assert len(a["tiles"]) + 12 <= 255, "tile ids no longer fit the uint8 tables"
    wide = False
    o.append("static const %s hudw_bgmap[%d][%d] = {" % ("uint16_t" if wide else "uint8_t", ROWS, COLS))
    for r in a["bgmap"]:
        o.append("  {" + ",".join(map(str, r)) + "},")
    o.append("};")
    o.append("static const uint32_t hudw_tiles[%d][8] = {" % len(a["tiles"]))
    for t in a["tiles"]:
        o.append("  {" + ",".join("0x%08XUL" % w for w in t) + "},")
    o.append("};")
    o.append("static const uint32_t hudw_faces[%d][12][8] = {" % len(a["faces"]))
    for f in a["faces"]:
        o.append(" {")
        for t in f:
            o.append("  {" + ",".join("0x%08XUL" % w for w in t) + "},")
        o.append(" },")
    o.append("};")
    o.append("#endif")
    return "\n".join(o) + "\n"


# ---- reference model of the compositor (the C code in hud_wad_logic.h is tested against this one) ---------------------------------
def model_rows(a, st):
    """st: dict(health, armor, ammo_r (-1 none), ammo[4], maxammo[4], arms (6-bit), keys (3-bit), face). -> 4 rows of 32 tile ids."""
    L, ids = LAYOUT, a["ids"]
    rows = [list(r) for r in a["bgmap"]]
    def big3(c0, v, pct):
        v = max(0, min(999, v))
        digs = [v // 100, v // 10 % 10, v % 10]
        lead = [v >= 100, v >= 10, True]
        for i in range(3):
            rows[0][c0 + i] = ids["big_top"][digs[i]] if lead[i] else ids["blank_top"]
            rows[1][c0 + i] = ids["big_bot"][digs[i]] if lead[i] else ids["blank_bot"]
        if pct:
            rows[0][c0 + 3], rows[1][c0 + 3] = ids["pct_top"], ids["pct_bot"]
    if st["ammo_r"] >= 0:
        big3(L["AMMO_C"], st["ammo_r"], False)
    big3(L["HEALTH_C"], st["health"], True)
    big3(L["ARMOR_C"], st["armor"], True)
    for i in range(6):
        r, c = L["ARMS_R"] + i // 3, L["ARMS_C"] + i % 3
        rows[r][c] = (ids["ysm"] if st["arms"] >> i & 1 else ids["gsm"])[i + 2]
    for k in range(3):
        rows[L["KEYS_R"] + k][L["KEYS_C"]] = ids["keys"][k if st["keys"] >> k & 1 else 3]
    n = len(a["tiles"])
    for r in range(4):
        for c in range(3):
            rows[L["FACE_R"] + r][L["FACE_C"] + c] = n + r * 3 + c       # VRAM face slot, filled from hud_faces[face]
    for t in range(4):
        for part, v in ((0, st["ammo"][t]), (1, st["maxammo"][t])):
            v = max(0, min(999, v))
            digs = [v // 100, v // 10 % 10, v % 10]
            lead = [v >= 100, v >= 10, True]
            for i in range(3):
                rows[L["TABLE_R"] + t][L["TABLE_C"] + part * 3 + i] = ids["ysm"][digs[i]] if lead[i] else ids["blank_small"]
    return rows


# ---- preview ---------------------------------------------------------------------------------------------------------------------
def render_rows_rgb(a, rows, face, scale=1):
    """Compose a preview image (list of RGB rows, 256x32) from tile ids with the quantised palette, face tiles from the face table."""
    pal = [((w >> 1 & 7) * 255 // 7, (w >> 5 & 7) * 255 // 7, (w >> 9 & 7) * 255 // 7) for w in [md_word(c) for c in a["palette"]]]
    L = LAYOUT
    img = [[(0, 0, 0)] * (COLS * 8) for _ in range(ROWS * 8)]
    for ty in range(ROWS):
        for tx in range(COLS):
            tid = rows[ty][tx]
            t = a["tiles"][tid] if tid < len(a["tiles"]) else a["faces"][face][tid - len(a["tiles"])]
            for y in range(8):
                for x in range(8):
                    img[ty * 8 + y][tx * 8 + x] = pal[(t[y] >> (28 - 4 * x)) & 15]
    if scale > 1:
        img = [[px for px in r for _ in range(scale)] for r in img for _ in range(scale)]
    return img


def write_png(path, img):
    h, w = len(img), len(img[0])
    raw = b"".join(b"\0" + bytes(c for px in r for c in px) for r in img)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                           chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


SAMPLE_STATES = [
    dict(health=100, armor=0, ammo_r=50, ammo=[50, 0, 0, 0], maxammo=[200, 50, 50, 300], arms=0b000001, keys=0, face=0),
    dict(health=63, armor=45, ammo_r=12, ammo=[120, 12, 5, 80], maxammo=[200, 50, 50, 300], arms=0b001111, keys=0b011, face=8 * 1 + 1),
    dict(health=12, armor=200, ammo_r=-1, ammo=[300, 50, 50, 300], maxammo=[400, 100, 100, 600], arms=0b111111, keys=0b111, face=8 * 4 + 5),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--wad", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview")
    a = ap.parse_args(argv)
    try:
        lumps = read_iwad(open(a.wad, "rb").read())
        assets = build_assets(lumps)
    except (WadError, OSError, struct.error, IndexError) as e:
        sys.exit("gen_hud_wad: %s" % e)
    open(a.out, "w").write(emit_header(assets))
    print("HUD assets: %d tiles, %d faces, bg %dx%d, palette %s" % (len(assets["tiles"]), len(assets["faces"]), COLS, ROWS,
                                                                    " ".join("%03X" % md_word(c) for c in assets["palette"])))
    if a.preview:
        imgs = [render_rows_rgb(assets, model_rows(assets, s), s["face"], 3) for s in SAMPLE_STATES]
        write_png(a.preview, [r for im in imgs for r in im + [[(40, 40, 40)] * len(im[0])] * 3])
        print("preview:", a.preview)
    return 0


if __name__ == "__main__":
    sys.exit(main())
