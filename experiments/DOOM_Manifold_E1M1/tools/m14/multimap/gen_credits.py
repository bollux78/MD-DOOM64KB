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
out = bytearray()
for name in ORDER:
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
