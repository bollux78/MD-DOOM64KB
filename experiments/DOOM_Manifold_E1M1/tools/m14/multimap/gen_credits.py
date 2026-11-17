#!/usr/bin/env python3
"""credits.bin: 4 full-screen images for the menu (title, credits 1, credits 2, end).
   Each blob = pal[64 words] | attr[1120 words, palette<<13] | tiles[1120 * 16 words] (same layout as inter.bin).
   Built from the Tile Palette Studio exports in credits_src/ (PNG + CRAM + per-tile palette CSV)."""
import csv, struct, os
from PIL import Image
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credits_src")
ORDER = ["titlescreenBOLLUX", "DoomCREDIT10", "disclaimer_and_credits", "endMD2"]
def cram_rgb(w):
    return (((w >> 1) & 7) * 34, ((w >> 5) & 7) * 34, ((w >> 9) & 7) * 34)
def auto_blob(png):
    """title from a plain 320x224 PNG (<=64 colours): packs tile colour sets into 4 palettes of 16 (no Tile Palette Studio export needed)."""
    import random
    im = Image.open(png).convert("RGB"); px = im.load()
    c9 = lambda r, g, b: ((b >> 5) << 9) | ((g >> 5) << 5) | ((r >> 5) << 1)
    tiles = {(tx, ty): frozenset(c9(*px[tx * 8 + x, ty * 8 + y]) for y in range(8) for x in range(8)) for ty in range(28) for tx in range(40)}
    keys = list(tiles)
    for attempt in range(500):
        random.seed(attempt); order = keys[:]; random.shuffle(order); order.sort(key=lambda k: -len(tiles[k]))
        pals = [[] for _ in range(4)]; asg = {}; ok = True
        for k in order:
            s = tiles[k]
            cand = [(len(s - set(pals[i])), len(pals[i]), i) for i in range(4) if len(set(pals[i]) | s) <= 16]
            if not cand: ok = False; break
            i = min(cand)[2]; pals[i] += [c for c in sorted(s) if c not in pals[i]]; asg[k] = i
        if ok: break
    else: raise SystemExit("title: cannot pack tiles into 4 palettes")
    cram = [pals[p][i] if i < len(pals[p]) else 0 for p in range(4) for i in range(16)]
    attrs = []; tl = []
    for ty in range(28):
        for tx in range(40):
            p = asg[(tx, ty)]; attrs.append(p << 13)
            for y in range(8):
                row = 0
                for x in range(8): row = (row << 4) | pals[p].index(c9(*px[tx * 8 + x, ty * 8 + y]))
                tl.append(row)
    print("title (auto)", png, "colours", len(set(cram)))
    return struct.pack(">64H", *cram) + struct.pack(">1120H", *attrs) + struct.pack(">%dI" % len(tl), *tl)
out = bytearray()
for name in ORDER:
    if name == ORDER[0] and os.environ.get("CREDITS_TITLE_PNG"):
        out += auto_blob(os.environ["CREDITS_TITLE_PNG"]); continue
    im = Image.open(os.path.join(D, name + "_pal.png")).convert("RGBA")
    cram = struct.unpack(">64H", open(os.path.join(D, name + "_pal.palettes.cram.be.bin"), "rb").read())
    pal_of = {}
    for r in csv.DictReader(open(os.path.join(D, name + "_pal_tile_palettes.csv"))):
        pal_of[(int(r["tile_x"]), int(r["tile_y"]))] = int(r["palette_0_to_3"])
    pr = [[cram_rgb(cram[p * 16 + i]) for i in range(16)] for p in range(4)]
    px = im.load()
    attrs = []; tiles = []; err = 0
    for ty in range(28):
        for tx in range(40):
            p = pal_of[(tx, ty)]; attrs.append(p << 13)
            for y in range(8):
                row = 0
                for x in range(8):
                    r, g, b, a = px[tx * 8 + x, ty * 8 + y]
                    best = min(range(16), key=lambda i: (pr[p][i][0] - r) ** 2 + (pr[p][i][1] - g) ** 2 + (pr[p][i][2] - b) ** 2)
                    err += (pr[p][best][0] - r) ** 2 + (pr[p][best][1] - g) ** 2 + (pr[p][best][2] - b) ** 2
                    row = (row << 4) | best
                tiles.append(row)
    print(name, "sq err/pixel %.2f" % (err / (320 * 224)))
    out += struct.pack(">64H", *cram) + struct.pack(">1120H", *attrs) + struct.pack(">%dI" % len(tiles), *tiles)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "credits.bin"), "wb").write(out)
print("credits.bin", len(out), "bytes, blob stride", len(out) // 4)
