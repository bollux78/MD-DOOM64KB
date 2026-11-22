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
import argparse, json, struct, math, os
from pathlib import Path
import numpy as np

NO_SECTOR = 0xFFFF

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wad", type=Path)
    parser.add_argument("map")
    parser.add_argument("output", type=Path)
    parser.add_argument("--geometry-only", action="store_true", help="Skip game-specific things")
    parser.add_argument("--skill", choices=("easy", "medium", "hard"),
                        default=os.environ.get("DREAD_SKILL", "medium"),
                        help="Doom THINGS skill flags: easy=1, medium=2, hard=4 (default: medium)")
    parser.add_argument("--row-only", action="store_true", help="Emit only byte-format textures")
    parser.add_argument("--palette", type=Path, help="JSON with 16 MD RGB triples (0–7)")
    parser.add_argument("--collect-items", type=Path, help="only save this map's colour samples (npz) for an episode palette")
    parser.add_argument("--fit-from", type=Path, nargs="+", help="fit one palette to these npz samples, write it to --palette-out and stop")
    parser.add_argument("--palette-out", type=Path)
    parser.add_argument("--tex-pad", type=int, default=0, help="store H + min(H, PAD) texels per column instead of 2H (episode builds)")
    args = parser.parse_args()
    skill_mask = {"easy": 1, "medium": 2, "hard": 4}[args.skill]
    wad = Wad(args.wad)
    mapname = args.map.upper()
    out = args.output
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
    if not 0 < len(secs) <= NO_SECTOR:
        raise ValueError(f"{mapname}: invalid sector count ({len(secs)})")
    if len(ssecs) > 4096:
        raise ValueError(f"{mapname}: exceeds the PVS generator's 4096 subsectors")
    if any(n > 65535 for n in map(len, (verts, lines, segs, nodes))):
        raise ValueError(f"{mapname}: exceeds a 16-bit geometry count")
    if any(side[-1] >= len(secs) for side in sides):
        raise ValueError(f"{mapname}: sidedef references a missing sector")
    texnames = sorted(used)
    if len(texnames) > 255:
        raise ValueError(f"{mapname}: {len(texnames)} wall textures exceed the byte index")
    teximg = {nm: compose(nm) for nm in texnames}

    flats = wad.range(("F_START", "FF_START"), ("F_END", "FF_END"))
    flatcol = {}
    for s in secs:
        for nm in (s[2], s[3]):
            if nm in flats and nm not in flatcol:
                f = np.frombuffer(flats[nm][:4096], np.uint8)
                flatcol[nm] = f

    # ---- things: select the requested original Doom skill flag, exclude multiplayer-only
    THING_SPR = {   # Doom type -> sprite prefix (frame A, front view)
        3004: "POSS", 9: "SPOS", 3001: "TROO", 3002: "SARG", 58: "SARG", 3006: "SKUL", 3005: "HEAD", 3003: "BOSS",
        2035: "BAR1", 2028: "COLU", 2018: "ARM1", 2019: "ARM2", 2014: "BON1", 2015: "BON2", 2011: "STIM", 2012: "MEDI",
        2007: "CLIP", 2008: "SHEL", 2048: "AMMO", 2049: "SBOX", 2010: "ROCK", 2046: "BROK", 2047: "CELL", 17: "CELP",
        2001: "SHOT", 2002: "MGUN", 2003: "LAUN", 2004: "PLAS", 2005: "CSAW", 2006: "BFUG", 8: "BPAK",
        2013: "SOUL", 2022: "PINV", 2023: "PSTR", 2024: "PINS", 2025: "SUIT", 2026: "PMAP", 2045: "PVIS",
        5: "BKEY", 6: "YKEY", 13: "RKEY", 38: "RSKU", 39: "YSKU", 40: "BSKU",
        34: "CAND", 35: "CBRA", 44: "TBLU", 45: "TGRN", 46: "TRED", 48: "ELEC", 30: "COL1", 31: "COL2", 32: "COL3",
        33: "COL4", 36: "COL5", 37: "COL6", 41: "CEYE", 42: "FSKU", 43: "TRE1", 47: "SMIT", 54: "TRE2", 55: "SMBT",
        56: "SMGT", 57: "SMRT", 10: "PLAY", 12: "PLAY", 15: "PLAY", 24: "POL5", 27: "POL4", 28: "POL2", 29: "POL3",
        25: "POL1", 26: "POL6", 18: "POSS", 19: "SPOS", 20: "TROO", 21: "SARG", 22: "HEAD", 23: "SKUL",
    }
    THING_FRAME = {10: "W", 12: "W", 15: "N", 18: "L", 19: "L", 20: "M", 21: "N", 22: "L", 23: "K"}
    MONSTERS = {3004, 9, 3001, 3002, 58, 3006, 3005, 3003}
    sprlumps = wad.range(("S_START", "SS_START"), ("S_END", "SS_END"))
    def sprite_lump(prefix, fr):
        for rot in "10":
            nm = prefix + fr + rot
            if nm in sprlumps: return sprlumps[nm]
            for k, v in sprlumps.items():          # combined rotations, e.g. POSSA2A8 (we want 1 or 0)
                if k.startswith(prefix + fr + rot) or (len(k) == 8 and k[4:6] == fr + rot and k.startswith(prefix)):
                    return v
        return None
    def sub_of(x, y):
        n = len(nodes) - 1
        while not (n & 0x8000):
            nx, ny, ndx, ndy = nodes[n][:4]
            side = 0 if ndy * (x - nx) > ndx * (y - ny) else 1
            n = nodes[n][12 + side]
        return n & 0x7FFF
    # ---- monsters: walk / attack / pain frames in rotations 1-5 (6-8 are drawn mirrored), death frames
    KINDS = [   # (Doom type, sprite, walk, attack, pain, death); index = kind in MapThing.flags bits 8-11
        (3004, "POSS", "ABCD", "EF", "G", "HIJKL"), (9, "SPOS", "ABCD", "EF", "G", "HIJKL"),
        (3001, "TROO", "ABCD", "EFG", "H", "IJKLM"), (3002, "SARG", "ABCD", "EFG", "H", "IJKLMN"),
        (58, "SARG", "ABCD", "EFG", "H", "IJKLMN"), (3006, "SKUL", "AB", "CD", "E", "FGHIJK"),
        (3003, "BOSS", "ABCD", "EFG", "H", "IJKLMNO"), (3005, "HEAD", "A", "BCD", "E", "GHIJKL"),
    ]
    KIND_OF = {k[0]: i for i, k in enumerate(KINDS)}
    MONSTER_BUCKET = 1                  # one light level for moving monsters (they change sectors)
    def frame_lump(prefix, letter, rot):
        """(patch, mirrored) for rotation rot (0..8) of a frame, from plain or combined lump names"""
        for nm, d in sprlumps.items():
            if not nm.startswith(prefix) or len(nm) < 6: continue
            if nm[4:6] == letter + str(rot): return d, False
            if len(nm) >= 8 and nm[6:8] == letter + str(rot): return d, True
        if rot:
            return frame_lump(prefix, letter, 0)
        return None, False
    def load_frame(key, prefix, letter, rot):
        if key in sprimg: return True
        d, mirror = frame_lump(prefix, letter, rot)
        if d is None: return False
        w_, h_, lo_, to_ = struct.unpack_from("<HHhh", d, 0)
        img = read_patch(d)
        if mirror: img = img[:, ::-1]; lo_ = w_ - lo_
        sprimg[key] = (img, lo_, to_); sprnames.append(key)
        return True
    thing_rows, sprnames, sprimg = [], [], {}
    mframes = [0xFFFF] * (len(KINDS) * 16 * 5)
    fx = [0xFFFF] * 19                   # imp ball A B, explosion C D E, baron ball A B, caco ball A
    kinds_present = sorted({KIND_OF[t[3]] for t in things if t[3] in KIND_OF and (t[4] & skill_mask) and not (t[4] & 16)})
    if not args.geometry_only:
        for k in kinds_present:
            _, prefix, walk, atk, pain, death = KINDS[k]
            for letter in walk + atk + pain + death:
                for r in range(5):
                    rot = 0 if letter in death else r + 1
                    key = (prefix, letter, rot)
                    if load_frame(key, prefix, letter, rot):
                        mframes[(k * 16 + ord(letter) - 65) * 5 + r] = sprnames.index(key)
        for slot, (prefix, letter, rot) in enumerate([("BAL1", "A", 0), ("BAL1", "B", 0), ("BAL1", "C", 0), ("BAL1", "D", 0),
                                                      ("BAL1", "E", 0), ("BAL7", "A", 1), ("BAL7", "B", 1), ("BAL2", "A", 0), ("MISL","A",1), ("MISL","B",0), ("MISL","C",0), ("MISL","D",0), ("SHOT","A",0), ("CLIP","A",0), ("BEXP","A",0), ("BEXP","B",0), ("BEXP","C",0), ("BEXP","D",0), ("BEXP","E",0)]):
            if load_frame((prefix, letter, rot), prefix, letter, rot): fx[slot] = sprnames.index((prefix, letter, rot))
    monster_sprites = {i for i in mframes if i != 0xFFFF} | {i for i in fx if i != 0xFFFF}
    for (tx, ty, ta, tt, tf) in (() if args.geometry_only else things):
        if tt not in THING_SPR or not (tf & skill_mask) or (tf & 16): continue
        if tt in KIND_OF:
            k = KIND_OF[tt]; si = mframes[(k * 16) * 5]
            if si == 0xFFFF: continue
            sub = sub_of(tx, ty)
            # flags: 1 monster, 2 ambush (wakes by sight only), bits 2-4 facing (0 = east, CCW), bits 8-11 kind
            thing_rows.append([tx, ty, si, sub, tt, 1 | (2 if tf & 8 else 0) | ((((ta + 22) // 45) & 7) << 2) | (k << 8)])
            continue
        key = (THING_SPR[tt], THING_FRAME.get(tt, "A"))
        if key not in sprimg:
            d = sprite_lump(*key)
            if d is None: continue
            w_, h_, lo_, to_ = struct.unpack_from("<HHhh", d, 0)
            sprimg[key] = (read_patch(d), lo_, to_)
            sprnames.append(key)
        sub = sub_of(tx, ty)
        ITEM = {2007: 1, 2048: 2, 2011: 3, 2012: 4, 2014: 5, 2015: 6, 2018: 7, 2019: 8, 2013: 9, 8: 10,
                5: 20, 6: 21, 13: 22, 38: 23, 39: 24, 40: 25, 2001: 30, 2002: 31, 2003: 32, 2005: 33, 2008: 40, 2049: 41, 2010: 42, 2046: 43, 2022:70,2023:71,2024:72,2025:73,2026:74,2045:75,2035:80}
        thing_rows.append([tx, ty, sprnames.index(key), sub, tt, ITEM.get(tt, 81 if tt in [-1, 3004, 9, 3001, 3002, 58, 3003, 2035, 2028, 46, 48, 35] else 0) << 8])
    # light bucket of each thing: its sector's
    spr_used = {}   # sprite index -> set(buckets)

    # ---- colour: NPAL palettes (one per 8x8 screen tile), each fitted FOR colour pairs.
    # Items = (texture, light bucket) and (flat, light bucket); every item gets one palette.
    NPAL = int(os.environ.get("DREAD_NPAL", "3"))
    MIXW = float(os.environ.get("DREAD_MIX_PENALTY", "0.08"))
    # Shared C7 palette: index 12 used to be medium gray (3,3,3).
    # Replace it with the *actual* SSF green 0x4C4 = MD RGB (2,6,2).
    # Only NUKEDGE* wall texels, BAL7 ball, BAR1 toxic barrel and the
    # green hair in living POSS zombieman sprite frames may use it.
    # All other colours are remapped OFFLINE to two existing colours.
    accent_green = os.environ.get("DREAD_GREEN_ACCENT", "0") == "1"
    accent_slot = 12
    if accent_green and args.palette:
        actual = json.loads(args.palette.read_text())
        if actual[accent_slot] != [2, 6, 2]:
            raise ValueError("DREAD_GREEN_ACCENT requires palette index 12 to be the SSF green (2,6,2)")
    accent_texture_count = 0
    accent_baronglow_count = 0
    accent_barrel_count = 0
    accent_zombie_hair_count = 0
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
    for (tx, ty, si, sub, tt, _f) in thing_rows:
        if si in monster_sprites: continue
        secn = sides[lines[segs[ssecs[sub][1]][3]][5 if segs[ssecs[sub][1]][4] == 0 else 6]][5]
        spr_used.setdefault(si, set()).add(bucket_of(secs[secn][4]))
    for si in monster_sprites:
        spr_used[si] = {0} if si in fx else {MONSTER_BUCKET}
    for si, bs_ in spr_used.items():
        img = sprimg[sprnames[si]][0]
        px = img[img >= 0].astype(np.int64)
        for b in bs_:
            if len(px): items.append((("p", si, b), np.repeat(pal[cmap[LIGHT_ROWS[b]][px]], 2, axis=0)))

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
            self.gray_fallback_pairs = np.array([i for i, (x, y) in enumerate(self.pairs)
                if accent_slot not in (x, y)], dtype=np.int16)
            self.mix = np.array([((lin[x] + lin[y]) / 2) ** (1 / 2.2) * 255.0 for x, y in self.pairs])
            self.spread = np.array([np.sqrt(((self.rgb[x] - self.rgb[y]) ** 2).sum()) for x, y in self.pairs])
        def cost(self, X):          # per-pixel error with the best pair
            d = np.sqrt(((X[:, None, :] - self.mix[None]) ** 2).sum(-1)) + MIXW * self.spread[None]
            return d.min(1)
        def pair(self, rgb, allow_accent=False):
            d = np.sqrt(((self.mix - rgb) ** 2).sum(-1)) + MIXW * self.spread
            if accent_green and not allow_accent:
                # Use pairs of other colours in lieu of the removed gray.
                p = int(self.gray_fallback_pairs[int(d[self.gray_fallback_pairs].argmin())])
            else:
                p = int(d.argmin())
            x, y = self.pairs[p]
            if self.rgb[x].sum() > self.rgb[y].sum(): x, y = y, x
            return x, y
        def byte(self, rgb):
            x, y = self.pair(rgb); return (x << 4) | y

    if args.collect_items:
        U2, w2 = summarize(np.concatenate([X for _, X in items]), 3000)
        np.savez(args.collect_items, U=U2, w=w2)
        print("colour samples: %d" % len(U2))
        return
    if args.fit_from:
        Us, ws = [], []
        for f in args.fit_from:
            z = np.load(f); Us.append(z["U"]); ws.append(z["w"])
        U2, w2 = np.concatenate(Us), np.concatenate(ws)
        if len(U2) > 1500:
            k = np.argsort(-w2)[:1500]; U2, w2 = U2[k], w2[k]
        ch, e = fit_palette(U2, w2)
        lv = [[int(v) for v in cand_lv[c]] for c in ch]
        args.palette_out.write_text(json.dumps(lv))
        print("episode palette: %d maps, mean pair error %.1f, %s" % (len(args.fit_from), e, lv))
        return
    if args.palette:
        levels = np.asarray(json.loads(args.palette.read_text()))
        if NPAL != 1 or levels.shape != (16, 3) or not np.issubdtype(levels.dtype, np.integer) or not ((0 <= levels) & (levels <= 7)).all():
            raise ValueError("A shared palette requires DREAD_NPAL=1 and 16 RGB triples in 0–7")
        pals = [Pal((levels @ [64, 8, 1]).tolist())]
        asg = np.zeros(len(items), dtype=int)
    else:
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
    def lut_for(b, k, green_asset=False, soft_green=False):
        key = (b, k, bool(green_asset), bool(soft_green))
        if key not in lut:
            pl = pals[k]
            out = []
            for i in range(256):
                rgb = pal[cmap[LIGHT_ROWS[b]][i]]
                # Require a recognisably saturated green source. Even for
                # target assets, don't recolour their metal/shadow/grays.
                if soft_green:
                    # Zombieman hair can have darker olive-green pixels.
                    green_pixel = (rgb[1] >= 52 and rgb[1] >= rgb[0] + 10
                                   and rgb[1] >= rgb[2] + 10)
                else:
                    green_pixel = (rgb[1] >= 78 and rgb[1] >= rgb[0] + 18
                                   and rgb[1] >= rgb[2] + 18)
                out.append(pl.pair(rgb, allow_accent=accent_green
                                   and green_asset and green_pixel))
            lut[key] = out
        return lut[key]

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
            # NUKEDGE textures are the green trim of Doom's acid pools.
            # Never allow accent-green into unrelated walls, floor, sky, HUD.
            is_acid_trim = accent_green and nm.startswith("NUKEDGE")
            L = lut_for(b, k, is_acid_trim)
            col = bytearray()
            for u in range(W2):
                sx = (u % hw) * 2
                one = bytearray()
                for v in range(H2):
                    pa, pb = L[img[v % h, sx]]
                    if is_acid_trim:
                        accent_texture_count += (pa == accent_slot) + (pb == accent_slot)
                    one.append(pa << 4 | pb)   # same order on every row: clean screen-aligned vertical lines
                col += one + (one[:min(len(one), args.tex_pad)] if args.tex_pad else one)   # repeated start: the scalers skip the wrap mask
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
        return sides[sd][5] if sd != 0xFFFF else NO_SECTOR

    seg_rows = []
    for (v1, v2, ang, ld, side, off) in segs:
        lv1, lv2, fl, sp, tg, r, l = lines[ld]
        fsd, bsd = (r, l) if side == 0 else (l, r)
        xo, yo, up, lo, mid, fs = sides[fsd]
        bs = sec_of_side(bsd) if (fl & 4) else NO_SECTOR
        t = lambda nm: tid.get(nm, 255)
        flags = (1 if fl & 8 else 0) | (2 if fl & 16 else 0) | (4 if bs != NO_SECTOR else 0) | (8 if sp==48 else 0)
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
    H.append("/* generated by conv.py from %s %s -- do not edit */" % (args.wad.name, mapname))
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
    # collision grid (128-unit cells): every line listed in the cells its bbox, grown by the player radius, touches
    BM, RAD = 128, 24
    xs_ = [v[0] for v in verts]; ys_ = [v[1] for v in verts]
    bx0, by0 = min(xs_) - RAD, min(ys_) - RAD
    bw, bh = (max(xs_) + RAD - bx0) // BM + 1, (max(ys_) + RAD - by0) // BM + 1
    cells = [[] for _ in range(bw * bh)]
    for i, l in enumerate(lines):
        ax, ay = verts[l[0]]; bx, by = verts[l[1]]
        for cy in range((min(ay, by) - RAD - by0) // BM, (max(ay, by) + RAD - by0) // BM + 1):
            for cx in range((min(ax, bx) - RAD - bx0) // BM, (max(ax, bx) + RAD - bx0) // BM + 1):
                cells[cy * bw + cx].append(i)
    offs, lst = [], []
    for c in cells: offs.append(len(lst)); lst += c
    offs.append(len(lst))
    H.append("const int16_t map_bm[4] = {%d,%d,%d,%d};" % (bx0, by0, bw, bh))
    H.append("const uint16_t map_bm_off[%d] = {%s};" % (len(offs), ",".join(map(str, offs))))
    H.append("const uint16_t map_bm_list[%d] = {%s};" % (max(1, len(lst)), ",".join(map(str, lst)) or "0"))
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
    # sprites: half width like the walls (one byte = a pair of MD colours, vertical-line mixing), per light
    # bucket: column table (w2 x uint16, offsets from the table) then posts {top, len, len bytes}, 0xFF ends
    sblob = bytearray(); srows = []
    for si, key in enumerate(sprnames):
        img, lo_, to_ = sprimg[key]
        h_, w_ = img.shape
        w2 = max(1, (w_ + 1) // 2)
        offs = []
        for b in range(len(LIGHT_ROWS)):
            if b not in spr_used.get(si, ()):
                offs.append(None); continue
            k = pal_of.get(("p", si, b), 0)
            # BAR1 is the poison/liquid barrel, BAL7 is the Baron shot.
            # Living POSS frames (A-G) have green hair; limit that accent
            # to the head region and *originally green* source pixels.
            # Do not tint faces, skin, clothing, metal, or corpse frames.
            is_baron_ball = accent_green and key[0] == "BAL7"
            is_poison_barrel = accent_green and key[0] == "BAR1"
            is_zombie = accent_green and key[0] == "POSS" and key[1] in "ABCDEFG"
            green_asset = is_baron_ball or is_poison_barrel
            L = lut_for(b, k, green_asset)
            hair_L = lut_for(b, k, True, True) if is_zombie else L
            base = len(sblob)
            cols = []
            for j in range(w2):
                col = bytearray(); y = 0; sx = min(2 * j, w_ - 1)
                while y < h_:
                    if img[y, sx] < 0: y += 1; continue
                    y1 = y
                    while y1 < h_ and img[y1, sx] >= 0 and y1 - y < 250: y1 += 1
                    run = bytearray()
                    for yy in range(y, y1):
                        # Restrict zombie green to upper quarter of sprite.
                        # Per-scanline source mapping is OFFLINE only.
                        is_hair_pixel = is_zombie and yy < max(4, h_ // 4)
                        src_lut = hair_L if is_hair_pixel else L
                        aa, bb = src_lut[img[yy, sx]]
                        if is_baron_ball:
                            accent_baronglow_count += (aa == accent_slot) + (bb == accent_slot)
                        if is_poison_barrel:
                            accent_barrel_count += (aa == accent_slot) + (bb == accent_slot)
                        if is_hair_pixel:
                            accent_zombie_hair_count += (aa == accent_slot) + (bb == accent_slot)
                        run.append((aa << 4) | bb)
                    col += bytes([y, y1 - y]) + run + run[-1:] * 3   # scaler padding
                    y = y1
                col.append(0xFF)
                cols.append(col)
            tab = bytearray(); pos = 2 * w2
            for col in cols: tab += struct.pack(">H", pos); pos += len(col)
            sblob += tab
            for col in cols: sblob += col
            if len(sblob) & 1: sblob.append(0xFF)
            offs.append(base)
        first = next((o for o in offs if o is not None), 0)
        offs = [o if o is not None else first for o in offs]
        srows.append((w2, h_, lo_, to_, offs))
    H.append("const uint8_t spr_blob[%d] = {%s};" % (max(2, len(sblob)), ",".join(map(str, sblob)) or "0,0"))
    H.append("const MapSprite map_sprites[%d] = {%s};" % (max(1, len(srows)), ",".join(
        "{%d,%d,%d,%d,{%s}}" % (r[0], r[1], r[2], r[3], ",".join(map(str, r[4]))) for r in srows) or "{0}"))
    thing_rows.sort(key=lambda t: t[3])
    H.append("const MapThing map_things[%d] = {%s};" % (max(1, len(thing_rows)), ",".join(
        "{%d,%d,%d,%d,%d}" % (t[0], t[1], t[2], t[3], t[5]) for t in thing_rows) or "{0}"))
    H.append("const uint16_t map_mframes[%d] = {%s};" % (len(mframes), ",".join(map(str, mframes))))
    H.append("const uint16_t map_fx[19] = {%s};" % ",".join(map(str, fx)))
    # REJECT (sector x sector, bit set = cannot see) and sound adjacency (two-sided lines without "block sound")
    rj = bytearray(lump.get("REJECT", b"")); need = (len(secs) * len(secs) + 7) // 8
    rj = (rj + bytes(need))[:need]
    H.append("const uint8_t map_reject[%d] = {%s};" % (max(1, need), ",".join(map(str, rj)) or "0"))
    adj = [set() for _ in secs]
    for (v1, v2, fl, sp, tg, r, l) in lines:
        if r != 0xFFFF and l != 0xFFFF and not (fl & 64):
            a_, b_ = sides[r][5], sides[l][5]
            if a_ != b_: adj[a_].add(b_); adj[b_].add(a_)
    aoff, alist = [], []
    for n_ in adj: aoff.append(len(alist)); alist += sorted(n_)
    aoff.append(len(alist))
    H.append("const uint16_t map_secadj_off[%d] = {%s};" % (len(aoff), ",".join(map(str, aoff))))
    H.append("const uint16_t map_secadj[%d] = {%s};" % (max(1, len(alist)), ",".join(map(str, alist)) or "0"))
    H.append("const uint16_t map_nthings = %d;" % len(thing_rows))
    soff = [0] * (len(ssecs) + 1)
    for t in thing_rows: soff[t[3] + 1] += 1   # (monsters too: their spawn list; the game moves them to RAM)
    for i in range(len(ssecs)): soff[i + 1] += soff[i]
    H.append("const uint16_t map_sub_things[%d] = {%s};" % (len(soff), ",".join(map(str, soff))))
    print("things: %d drawn (%d monsters), %d sprites %s, sprite blob %d bytes" % (len(thing_rows), sum(t[5] & 1 for t in thing_rows), len(srows), "".join(k[0] + k[1] + (str(k[2]) if len(k) > 2 else "") + " " for k in sprnames if len(k) == 2 or k[2] <= 1), len(sblob)))
    H.append("const uint8_t tex_blob[%d] = {%s};" % (len(blob), ",".join(str(x) for x in blob)))
    # same texels as words (b, b): column-doubled modes write 4 pixels per texel with one move.w
    if not args.row_only:
        H.append("const uint16_t tex_blob_w[%d] = {%s};" % (len(blob), ",".join(str(x * 257) for x in blob)))
    H.append("const MapTex map_tex[%d] = {%s};" % (max(1, len(texmeta)), ",".join(
        "{%d,%d,%d,%d,{%s},{%s}}" % (m[0], m[1], m[2], m[3], ",".join(str(o) for o in m[4]), ",".join(str(x) for x in m[5])) for m in texmeta) or "{0}"))
    H.append("const int16_t sintab[1024] = {%s};" % ",".join(str(int(round(16384 * math.sin(i * 2 * math.pi / 1024)))) for i in range(1024)))
    H.append("const int16_t map_start[3] = {%d,%d,%d};" % (start[0], start[1], start[2]))
    H.append("const uint16_t map_counts[6] = {%d,%d,%d,%d,%d,%d};" % (
        len(verts), len(seg_rows), len(ssecs), len(nodes), len(sec_rows), len(lines)))
    (out / "mapdata.c").write_text("\n".join(H) + "\n")
    # sizes the renderer's per-vertex caches exactly (RAM budget)
    (out / "mapcounts.h").write_text("#define MAP_NVERTS %d\n#define MAP_NSECTORS %d\n" % (len(verts), len(sec_rows)))

    print("map %s: %d verts %d segs %d subsectors %d nodes %d sectors %d lines; %d textures, texture blob %d bytes; sky %d"
          % (mapname, len(verts), len(seg_rows), len(ssecs), len(nodes), len(sec_rows), len(lines), len(texnames), len(blob), skycol))
    for k, pl in enumerate(pals): print("palette", k, pl.lv)
    if accent_green:
        print("C7 GREEN ACCENT 0x4C4: map", mapname,
              "NUKEDGE texels", accent_texture_count,
              "BAL7 sprite texels", accent_baronglow_count,
              "BAR1 barrel texels", accent_barrel_count,
              "POSS hair texels", accent_zombie_hair_count,
              "other assets: reserved slot excluded")
        if accent_baronglow_count == 0 and not args.geometry_only:
            raise ValueError("C7 accent produced no green texels in BAL7 sprites")


if __name__ == "__main__":
    main()
