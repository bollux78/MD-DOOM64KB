#!/usr/bin/env python3
"""Only the background of the status bar (no face, no numbers): the original STBAR (alone, and with the STARMS plate) at 320x32,
and the recreation's background tiles at 256x32. Same base64 dump as hud_images.py."""
import argparse, base64, struct, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gen_hud_wad as g
from hud_images import indexed_png


def stbar(lumps, with_arms):
    pp = lumps["PLAYPAL"]
    pal = [tuple(pp[3 * i:3 * i + 3]) for i in range(256)]
    img = [[(0, 0, 0)] * 320 for _ in range(32)]
    for name, x0 in (("STBAR", 0), ("STARMS", 104)) if with_arms else (("STBAR", 0),):
        if name not in lumps:
            continue
        w, h, rows = g.decode_patch(lumps[name])
        for y in range(min(h, 32)):
            for x in range(w):
                if rows[y][x] >= 0 and x0 + x < 320:
                    img[y][x0 + x] = pal[rows[y][x]]
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wad", required=True)
    ap.add_argument("--out-orig", required=True)
    ap.add_argument("--out-cur", required=True)
    ap.add_argument("--b64")
    a = ap.parse_args()
    lumps = g.read_iwad(open(a.wad, "rb").read())
    assets = g.build_assets(lumps)
    gap = [[(40, 40, 40)] * 320] * 2
    o = stbar(lumps, False) + gap + stbar(lumps, True)
    c = g.render_rows_rgb(assets, [list(r) for r in assets["bgmap"]], 0, 1)
    do, dc = indexed_png(a.out_orig, o), indexed_png(a.out_cur, c)
    print("bg orig", len(do), "bytes; bg cur", len(dc), "bytes")
    if a.b64:
        open(a.b64, "w").write("ORIG " + base64.b64encode(do).decode() + "\nCUR " + base64.b64encode(dc).decode() + "\n")


if __name__ == "__main__":
    main()
