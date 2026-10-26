#!/usr/bin/env python3
"""Side-by-side material for judging the recreated HUD: (1) the original status bar composed from the IWAD patches at
native 320x32, (2) the current recreation (256x32). Both for the same three sample states. Output: two indexed PNGs and
an optional base64 dump (for CI annotations, since artifacts cannot be downloaded through the review proxy).
Reads the user's IWAD only; nothing derived from it is committed."""
import argparse, base64, struct, sys, zlib
sys.path.insert(0, __import__("os").path.dirname(__file__))
import gen_hud_wad as g


def indexed_png(path, img):
    cols = sorted({px for r in img for px in r})
    assert len(cols) <= 256
    idx = {c: i for i, c in enumerate(cols)}
    h, w = len(img), len(img[0])
    raw = b"".join(b"\0" + bytes(idx[px] for px in r) for r in img)
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0)) +
            ch(b"PLTE", bytes(c for col in cols for c in col)) + ch(b"IDAT", zlib.compress(raw, 9)) + ch(b"IEND", b""))
    open(path, "wb").write(data)
    return data


def original(lumps, st):
    pp = lumps["PLAYPAL"]
    pal = [tuple(pp[3 * i:3 * i + 3]) for i in range(256)]
    img = [[(0, 0, 0)] * 320 for _ in range(32)]

    def put(name, x, y, use_offsets=False):
        if name not in lumps:
            return 0
        b = lumps[name]
        w, h, rows = g.decode_patch(b)
        lo, to = struct.unpack_from("<hh", b, 4)
        if use_offsets:
            x, y = x - lo, y - to
        for yy in range(h):
            for xx in range(w):
                v = rows[yy][xx]
                if v >= 0 and 0 <= y + yy < 32 and 0 <= x + xx < 320:
                    img[y + yy][x + xx] = pal[v]
        return w

    def num(prefix, v, right, y, w, pct=False):
        v = max(0, min(999, v))
        s = str(v)
        x = right - w * len(s)
        for ch_ in s:
            put(prefix + ch_, x, y)
            x += w
        if pct:
            put("STTPRCNT", right, y)

    put("STBAR", 0, 0)
    put("STARMS", 104, 0)
    if st["ammo_r"] >= 0:
        num("STTNUM", st["ammo_r"], 44, 3, 14)
    num("STTNUM", st["health"], 90, 3, 14, True)
    num("STTNUM", st["armor"], 221, 3, 14, True)
    for i in range(6):
        pre = "STYSNUM" if (st["arms"] >> i) & 1 else "STGNUM"
        put(pre + str(i + 2), 111 + (i % 3) * 12, 4 + (i // 3) * 10)
    for i in range(4):
        num("STYSNUM", st["ammo"][i], 288, 5 + 6 * i, 4)
        num("STYSNUM", st["maxammo"][i], 314, 5 + 6 * i, 4)
    for k in range(3):
        if (st["keys"] >> k) & 1:
            put("STKEYS%d" % k, 239, 3 + 10 * k)
    put(g.FACE_NAMES[st["face"]], 143, 0, True)
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
    gap = lambda w: [[(40, 40, 40)] * w] * 2
    o, c = [], []
    for s in g.SAMPLE_STATES:
        o += original(lumps, s) + gap(320)
        c += g.render_rows_rgb(assets, g.model_rows(assets, s), s["face"], 1) + gap(256)
    do, dc = indexed_png(a.out_orig, o), indexed_png(a.out_cur, c)
    print("orig.png", len(do), "bytes; cur.png", len(dc), "bytes")
    if a.b64:
        open(a.b64, "w").write("ORIG " + base64.b64encode(do).decode() + "\nCUR " + base64.b64encode(dc).decode() + "\n")


if __name__ == "__main__":
    main()
