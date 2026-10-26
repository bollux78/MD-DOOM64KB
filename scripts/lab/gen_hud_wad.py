#!/usr/bin/env python3
"""Recreate the Doom status bar for the Mega Drive from the original IWAD (not committed: read at build time).

Reads the status-bar patches of a Doom IWAD (STBAR, STTNUM*, STYSNUM*, STGNUM*, STKEYS*, STF* faces), resamples them onto the 8x8 tile
grid of the VDP, quantises the background/digits to CRAM line 3 and the faces to CRAM line 2 (index 0 = black; background and faces are
Floyd-Steinberg dithered, the face square is a flat colour) and writes a C header with ROM tables:

    hud_pal[16]            CRAM words (0x0BGR) for palette line 3 (background, digits, keys)
    hud_fpal[16]           CRAM words for palette line 2 (faces)
    hud_tiles[N][8]        static tiles: background, big digits (8x16 as top/bottom tiles), small digits, keys, blanks
    hud_bgmap[4][32]       background tile ids (index into hud_tiles) of the 32x4-cell bar
    hud_faces[42][16][8]   face frames, 4 x 4 tiles each, uploaded to a 16-tile VRAM slot when the face changes

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
    BIG_Y=4,                     # big digits are drawn 4 px below the top of the bar (original: 3), over the dithered background
    FACE_C=14, FACE_R=0,         # 4 x 4 tiles: the 24 x 29 face is centred in 32 x 32, black round it, frame kept on top
    FACE_W=4,
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
            if bg is None:                       # sprite mode: opaque (pure sprite colour) where at least half is covered, else transparent
                row.append(tuple(int(round(acc[k] / cov)) for k in range(3)) if a >= 0.5 and cov > 0 else None)
                continue
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
    if "STARMS" in lumps:                     # the ARMS plate is a separate patch drawn over STBAR at (104, 0)
        aw, ah, arows = decode_patch(lumps["STARMS"])
        apx = patch_rgb(arows, pal)
        for y in range(min(ah, len(stbar))):
            for x in range(aw):
                if apx[y][x] is not None and 104 + x < len(stbar[0]):
                    stbar[y][104 + x] = apx[y][x]
    sw, sh = P["STBAR"][0], P["STBAR"][1]
    # 1. the background: STBAR squeezed to 256 x 32 (4/5 horizontally), vertically cropped/padded to 32.
    black = (0, 0, 0)
    bar = box_resample([[px if px is not None else black for px in r] for r in stbar], COLS * 8, ROWS * 8, black)
    # panel colours behind the widgets, sampled from the squeezed bar so the tiles blend in
    L = LAYOUT
    panel_small = median_color(bar, L["TABLE_C"] * 8, 0, (L["TABLE_C"] + 6) * 8, 32)    # flat panel behind the ammo-table digits
    panel_face = (0, 0, 0)                                    # the face square is black
    frame_face = median_color(bar, L["FACE_C"] * 8, 0, (L["FACE_C"] + L["FACE_W"]) * 8, 2)   # top frame line, kept above the face
    # 2. widget glyph images
    def glyph(name, dw, dh):
        return box_resample(rgb(name), dw, dh, None)       # transparent where the patch is: the dithered bar shows through
    big = {}
    for d in range(10):
        big[d] = glyph("STTNUM%d" % d, 8, 16)
    big["%"] = glyph("STTPRCNT", 8, 16)
    keyg = [(P["STKEYS%d" % k][0], P["STKEYS%d" % k][1], rgb("STKEYS%d" % k)) for k in range(3)]
    armsg = {}                                           # ARMS digits keep their native size; centred in the plate boxes by build_assets
    for d in range(2, 8):
        armsg["y%d" % d] = (P["STYSNUM%d" % d][0], P["STYSNUM%d" % d][1], rgb("STYSNUM%d" % d))
        armsg["g%d" % d] = (P["STGNUM%d" % d][0], P["STGNUM%d" % d][1], rgb("STGNUM%d" % d))
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
    ysm[" "] = solid(8, 8, panel_small)
    faces, fmasks = [], []
    for n in FACE_NAMES:
        g = rgb(n)
        w, h = P[n][0], P[n][1]
        FW = L["FACE_W"] * 8
        img = solid(FW, 32, panel_face)
        for y in range(2):
            for x in range(FW):
                img[y][x] = frame_face                       # the two top rows stay the HUD frame
        mask = [[False] * FW for _ in range(32)]             # True = face art; False = flat (black, or the frame on the top rows)
        ox, oy = (FW - w) // 2, min(2, 32 - h)               # centred; 2 px down so the frame above is not covered
        for y in range(h):
            for x in range(w):
                if g[y][x] is not None and 0 <= ox + x < FW and 0 <= oy + y < 32:
                    img[oy + y][ox + x] = g[y][x]
                    mask[oy + y][ox + x] = True
        faces.append(img)
        fmasks.append(mask)
    return dict(bar=bar, big=big, armsg=armsg, keyg=keyg, ysm=ysm, faces=faces, fmasks=fmasks, panel_small=panel_small, panel_face=panel_face, frame_face=frame_face)


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


def _dist(a, b):
    return 2 * (a[0] - b[0]) ** 2 + 4 * (a[1] - b[1]) ** 2 + 3 * (a[2] - b[2]) ** 2


def fs_dither(img, pal, mask=None, flat=None, strength=1.0):
    """Serpentine Floyd-Steinberg onto the palette `pal` (list of RGB). Pixels with mask False are set to the palette entry nearest
    to `flat` and neither receive nor spread error (a flat colour box stays flat)."""
    h, w = len(img), len(img[0])
    buf = [[[float(v) for v in px] for px in r] for r in img]
    out = [[None] * w for _ in range(h)]
    near = lambda c: min(pal, key=lambda p: (_dist(p, c), p))
    for y in range(h):
        xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
        d = 1 if y % 2 == 0 else -1
        for x in xs:
            if mask is not None and not mask[y][x]:
                out[y][x] = near(flat[y][x]) if isinstance(flat, list) else near(flat)
                continue
            old = tuple(0 if v < 0 else 255 if v > 255 else int(round(v)) for v in buf[y][x])
            new = near(old)
            out[y][x] = new
            err = [(old[i] - new[i]) * strength for i in range(3)]
            for dx, dy, f in ((d, 0, 7 / 16), (-d, 1, 3 / 16), (0, 1, 5 / 16), (d, 1, 1 / 16)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and (mask is None or mask[yy][xx]):
                    for i in range(3):
                        buf[yy][xx][i] += err[i] * f
    return out


def md_word(c):
    return ((c[2] >> 5) << 9) | ((c[1] >> 5) << 5) | ((c[0] >> 5) << 1)


def build_assets(lumps):
    im = build_images(lumps)
    L = LAYOUT
    # static background tile cells: the squeezed STBAR, with every dynamic cell replaced by the blank panel tile of its widget
    # CRAM line 3 serves the background, digits, keys; the faces get their own line (2). Floyd-Steinberg (100 %) on the background only;
    # glyphs stay crisp (nearest colour); the face square is a flat colour.
    hist3 = {}
    for r in range(ROWS * 8):
        for c in range(COLS * 8):
            if not (L["FACE_C"] * 8 <= c < (L["FACE_C"] + L["FACE_W"]) * 8):
                hist3[im["bar"][r][c]] = hist3.get(im["bar"][r][c], 0) + 1
    glyphs = list(im["big"].values()) + list(im["ysm"].values()) + [v[2] for v in im["armsg"].values()] + [v[2] for v in im["keyg"]]
    for gimg in glyphs:
        for r in gimg:
            for c in r:
                if c is not None:
                    hist3[c] = hist3.get(c, 0) + 4      # glyph colours (reds, yellows, card colours) must keep a palette slot
    palette = [(0, 0, 0)] + quantise_palette(hist3)
    while len(palette) < 16:
        palette.append((0, 0, 0))
    bar = fs_dither(im["bar"], palette[1:])
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
    def over(base, sprites):
        """base tile (8x8 RGB) with sprites (img with None = transparent, x, y relative to the tile) drawn over it."""
        px = [list(r) for r in base]
        for img, sx, sy in sprites:
            for yy, row in enumerate(img):
                for xx, v in enumerate(row):
                    X, Y = sx + xx, sy + yy
                    if v is not None and 0 <= X < 8 and 0 <= Y < 8:
                        px[Y][X] = v
        return tuple(tuple(r) for r in px)
    def comp_tile(tx, ty, sprites):
        """The dithered bar cell (tx, ty) with sprites given in bar pixels drawn over it."""
        return over(tile_of(bar, tx, ty), [(img, sx - tx * 8, sy - ty * 8) for img, sx, sy in sprites])
    # Big digits sit over ONE stone tile per tile row (taken from the HEALTH panel, above its label), so a digit tile is the same for every
    # position and widget: 10 digits x 3 rows + percent, not one per position. Digits are drawn BIG_Y px below the top of the bar.
    BY = L["BIG_Y"]
    assert BY + 16 <= 24
    stone = [tile_of(bar, L["HEALTH_C"] + 1, min(r, 1)) for r in range(4)]
    ids["stone"] = [add(stone[r]) for r in range(3)]
    ids["big"] = [[add(over(stone[r], [(im["big"][d], 0, BY - 8 * r)])) for r in range(3)] for d in range(10)]     # [digit][row]
    ids["pct"] = [add(over(stone[r], [(im["big"]["%"], 0, BY - 8 * r)])) for r in range(3)]
    # Boolean widgets over the real bar cells: the six ARMS digits (grey = not owned, yellow = owned), centred on the boxes of the STARMS
    # plate (original digit at x = 111 + 12 i, y = 4 + 10 j, bar squeezed 0.8), and the three key cards (nothing / card) at x = 239, y = 3 + 10 k.
    widgets = []
    for i in range(6):
        pos = {}
        for state, pre in ((0, "g"), (1, "y")):
            w, h, img = im["armsg"]["%s%d" % (pre, i + 2)]
            ow, oh = im["armsg"]["y%d" % (i + 2)][0], im["armsg"]["y%d" % (i + 2)][1]
            cx, cy = (111 + 12 * (i % 3) + ow / 2.0) * 0.8, 4 + 10 * (i // 3) + oh / 2.0
            pos[state] = (img, int(round(cx - w / 2.0)), int(round(cy - h / 2.0)), w, h)
        widgets.append(dict(bit=i, pos=pos))
    for k in range(3):
        kw, kh, kimg = im["keyg"][k]
        widgets.append(dict(bit=6 + k, pos={0: None, 1: (kimg, int(round(239 * 0.8)), 3 + 10 * k, kw, kh)}))
    cells = {}
    for wi, wd in enumerate(widgets):
        for st in (0, 1):
            if wd["pos"][st] is None:
                continue
            _img, sx, sy, w, h = wd["pos"][st]
            for ty in range(sy // 8, (sy + h - 1) // 8 + 1):
                for tx in range(sx // 8, (sx + w - 1) // 8 + 1):
                    if wi not in cells.setdefault((tx, ty), []):
                        cells[(tx, ty)].append(wi)
    wid_cells = []
    for (tx, ty), bl in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        assert len(bl) <= 2, "a tile may overlap at most two widgets"
        vs = []
        for v in range(4):
            sprites = []
            for k, wi in enumerate(bl):
                pp = widgets[wi]["pos"][(v >> k) & 1]
                if pp is not None:
                    sprites.append((pp[0], pp[1], pp[2]))
            vs.append(add(comp_tile(tx, ty, sprites)))
        wid_cells.append(dict(col=tx, row=ty, b0=widgets[bl[0]]["bit"], b1=widgets[bl[1]]["bit"] if len(bl) > 1 else 255, ids=vs))
    ids["wid"] = wid_cells
    # ammo table: small digits over a stone tile per row
    ids["ysm"] = [[add(over(stone[r], [(im["ysm"][d], 0, 0)])) for d in range(10)] for r in range(4)]     # [row][digit]
    ids["blank_small"] = [add(stone[r]) for r in range(4)]
    n_dynamic = len(tiles_rgb)
    bg_ids = [[0] * COLS for _ in range(ROWS)]
    over_cells = {}                                       # cells whose background is a shared stone tile
    for c0 in (L["AMMO_C"], L["HEALTH_C"], L["ARMOR_C"]):
        for i in range(4):
            for r in range(3):
                over_cells[(c0 + i, r)] = stone[r]
    for t in range(4):
        for i in range(6):
            over_cells[(L["TABLE_C"] + i, t)] = stone[t]
    flat_face = tuple(tuple((0, 0, 0) for _ in range(8)) for _ in range(8))
    for i in range(L["FACE_W"]):
        for rr in range(4):
            over_cells[(L["FACE_C"] + i, rr)] = flat_face
    for ty in range(ROWS):
        for tx in range(COLS):
            bg_ids[ty][tx] = add(over_cells[(tx, ty)] if (tx, ty) in over_cells else tile_of(bar, tx, ty))
    # face frames: own 15 colours + black (CRAM line 2), Floyd-Steinberg from the original patches, flat panel outside the face art
    fhist = {}
    for img, mask in zip(im["faces"], im["fmasks"]):
        for y in range(32):
            for x in range(24):
                if mask[y][x]:
                    fhist[img[y][x]] = fhist.get(img[y][x], 0) + 1
    snap = lambda c: tuple(min(255, (c[i] >> 5) * 255 // 7) for i in range(3))
    fcentres = quantise_palette(fhist, k=13) + [(0, 0, 0), snap(im["frame_face"])]     # + black square + frame line
    fpal = [(0, 0, 0)] + fcentres
    while len(fpal) < 16:
        fpal.append((0, 0, 0))
    face_tiles = []
    for img, mask in zip(im["faces"], im["fmasks"]):
        flat = [[snap(im["frame_face"]) if y < 2 else (0, 0, 0) for x in range(L["FACE_W"] * 8)] for y in range(32)]
        d = fs_dither(img, fpal[1:], mask, flat)
        face_tiles.append([tile_of(d, tx, ty) for ty in range(4) for tx in range(L["FACE_W"])])
    dist = _dist
    cache = {}
    def nearest(c):
        if c not in cache:
            cache[c] = min(range(16), key=lambda i: (dist(c, palette[i]), i))
        return cache[c]
    def pack(t):
        return [sum(nearest(t[y][x]) << (28 - 4 * x) for x in range(8)) for y in range(8)]
    fcache = {}
    def fnearest(c):
        if c not in fcache:
            fcache[c] = min(range(16), key=lambda i: (dist(c, fpal[i]), i))
        return fcache[c]
    def fpack(t):
        return [sum(fnearest(t[y][x]) << (28 - 4 * x) for x in range(8)) for y in range(8)]
    return dict(palette=palette, fpalette=fpal, tiles=[pack(t) for t in tiles_rgb], tiles_rgb=tiles_rgb, ids=ids, bgmap=bg_ids,
                faces=[[fpack(t) for t in ft] for ft in face_tiles], n_dynamic=n_dynamic)


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
    nest = lambda x: "{" + ",".join(nest(e) if isinstance(e, list) else str(e) for e in x) + "}"
    o.append("static const uint16_t hudw_big[10][3] = %s;   /* [digit][tile row]: glyph over the shared stone tile */" % nest(ids["big"]))
    o.append("static const uint16_t hudw_pct[3] = %s;" % nest(ids["pct"]))
    o.append("static const uint16_t hudw_ysm[4][10] = %s;   /* ammo table: [row][digit] */" % nest(ids["ysm"]))
    o.append("static const uint16_t hudw_blank_small[4] = %s;" % nest(ids["blank_small"]))
    wc = ids["wid"]
    o.append("#define HUDW_NWID %d   /* tiles that depend on the owned bits: ARMS digits (bits 0..5) and key cards (bits 6..8) */" % len(wc))
    o.append("static const uint8_t hudw_wid_col[%d] = {%s};" % (len(wc), ",".join(str(c["col"]) for c in wc)))
    o.append("static const uint8_t hudw_wid_row[%d] = {%s};" % (len(wc), ",".join(str(c["row"]) for c in wc)))
    o.append("static const uint8_t hudw_wid_b0[%d] = {%s};" % (len(wc), ",".join(str(c["b0"]) for c in wc)))
    o.append("static const uint8_t hudw_wid_b1[%d] = {%s};   /* 255: one widget only */" % (len(wc), ",".join(str(c["b1"]) for c in wc)))
    o.append("static const uint16_t hudw_wid_id[%d][4] = {%s};   /* tile for each combination of the two widgets' bits */" % (len(wc), ",".join("{" + ",".join(map(str, c["ids"])) + "}" for c in wc)))
    o.append("static const uint16_t hudw_pal[16] = {%s};" % ",".join("0x%04X" % md_word(c) for c in a["palette"]))
    o.append("static const uint16_t hudw_fpal[16] = {%s};" % ",".join("0x%04X" % md_word(c) for c in a["fpalette"]))
    assert len(a["tiles"]) + 4 * L["FACE_W"] <= 1440 - 800, "tiles no longer fit the free VRAM range"
    o.append("static const uint16_t hudw_bgmap[%d][%d] = {" % (ROWS, COLS))
    for r in a["bgmap"]:
        o.append("  {" + ",".join(map(str, r)) + "},")
    o.append("};")
    o.append("static const uint32_t hudw_tiles[%d][8] = {" % len(a["tiles"]))
    for t in a["tiles"]:
        o.append("  {" + ",".join("0x%08XUL" % w for w in t) + "},")
    o.append("};")
    o.append("static const uint32_t hudw_faces[%d][16][8] = {" % len(a["faces"]))
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
        for r in range(3):
            for i in range(3):
                if lead[i]:
                    rows[r][c0 + i] = ids["big"][digs[i]][r]
            if pct:
                rows[r][c0 + 3] = ids["pct"][r]
    if st["ammo_r"] >= 0:
        big3(L["AMMO_C"], st["ammo_r"], False)
    big3(L["HEALTH_C"], st["health"], True)
    big3(L["ARMOR_C"], st["armor"], True)
    mask = st["arms"] | (st["keys"] << 6)
    for c in ids["wid"]:
        v = (mask >> c["b0"] & 1) | ((mask >> c["b1"] & 1) << 1 if c["b1"] != 255 else 0)
        rows[c["row"]][c["col"]] = c["ids"][v]
    n = len(a["tiles"])
    for r in range(4):
        for c in range(L["FACE_W"]):
            rows[L["FACE_R"] + r][L["FACE_C"] + c] = n + r * L["FACE_W"] + c       # VRAM face slot, filled from hud_faces[face]
    for t in range(4):
        for part, v in ((0, st["ammo"][t]), (1, st["maxammo"][t])):
            v = max(0, min(999, v))
            digs = [v // 100, v // 10 % 10, v % 10]
            lead = [v >= 100, v >= 10, True]
            for i in range(3):
                if lead[i]:
                    rows[L["TABLE_R"] + t][L["TABLE_C"] + part * 3 + i] = ids["ysm"][t][digs[i]]
    return rows


# ---- preview ---------------------------------------------------------------------------------------------------------------------
def render_rows_rgb(a, rows, face, scale=1):
    """Compose a preview image (list of RGB rows, 256x32) from tile ids with the quantised palette, face tiles from the face table."""
    rgbp = lambda pl: [((w >> 1 & 7) * 255 // 7, (w >> 5 & 7) * 255 // 7, (w >> 9 & 7) * 255 // 7) for w in [md_word(c) for c in pl]]
    pal3, pal2 = rgbp(a["palette"]), rgbp(a["fpalette"])
    L = LAYOUT
    img = [[(0, 0, 0)] * (COLS * 8) for _ in range(ROWS * 8)]
    for ty in range(ROWS):
        for tx in range(COLS):
            tid = rows[ty][tx]
            isface = tid >= len(a["tiles"])
            t = a["faces"][face][tid - len(a["tiles"])] if isface else a["tiles"][tid]
            pal = pal2 if isface else pal3
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
