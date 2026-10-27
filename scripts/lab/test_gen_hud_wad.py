#!/usr/bin/env python3
"""Host tests for gen_hud_wad.py with a SYNTHETIC IWAD (the real WAD is not available here): patch codec round trip, asset build, palette,
header emission, compositor model, PNG preview."""
import os, sys, tempfile, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_hud_wad as G


def synthetic_lumps(seed=1):
    rnd = random.Random(seed)
    pal = bytearray()
    for i in range(256):                       # a smooth ramp palette
        pal += bytes([(i * 3) & 255, (i * 5) & 255, (i * 7) & 255])
    L = [("PLAYPAL", bytes(pal))]
    def patch(w, h, fill, hole=0.0):
        rows = [[(fill(x, y) if rnd.random() >= hole else -1) for x in range(w)] for y in range(h)]
        return G.encode_patch(rows)
    L.append(("STBAR", patch(320, 32, lambda x, y: 100 + ((x // 20 + y // 8) % 5) * 6)))
    for i in range(10):
        L.append(("STTNUM%d" % i, patch(14, 16, lambda x, y, i=i: 200 + i if (x + y + i) % 3 else 40, hole=0.35)))
    L.append(("STTPRCNT", patch(14, 16, lambda x, y: 220, hole=0.5)))
    for i in range(10):
        L.append(("STYSNUM%d" % i, patch(4, 6, lambda x, y, i=i: 230 + i % 3, hole=0.3)))
        L.append(("STGNUM%d" % i, patch(4, 6, lambda x, y, i=i: 90 + i % 3, hole=0.3)))
    for k in range(3):
        L.append(("STKEYS%d" % k, patch(7, 6, lambda x, y, k=k: 20 + 80 * k)))
    for n in G.FACE_NAMES:
        L.append((n, patch(24, 30, lambda x, y, n=n: 150 + (sum(map(ord, n)) % 40) + (x + y) % 7, hole=0.05)))
    return L


def test_codec():
    rows = [[-1, 3, 3, -1], [5, 5, -1, 7], [-1, -1, -1, -1]]
    b = G.encode_patch(rows)
    w, h, back = G.decode_patch(b)
    assert (w, h) == (4, 3) and back == rows, back


def test_iwad_roundtrip():
    lumps = synthetic_lumps()
    data = G.make_iwad(lumps)
    got = G.read_iwad(data)
    assert set(got) == {n for n, _ in lumps} and got["STBAR"] == dict(lumps)["STBAR"]


def test_assets_and_header():
    a = G.build_assets(G.read_iwad(G.make_iwad(synthetic_lumps())))
    assert len(a["faces"]) == 42 and all(len(f) == 16 for f in a["faces"])
    assert len(a["tiles"]) + 16 <= 1440 - 800, len(a["tiles"])
    assert len(a["palette"]) == 16 and a["palette"][0] == (0, 0, 0)
    assert all(0 <= w < 2 ** 32 for t in a["tiles"] for w in t)
    # every background id is a valid static tile
    assert all(0 <= v < len(a["tiles"]) for r in a["bgmap"] for v in r)
    h = G.emit_header(a)
    for needle in ("hudw_pal[16]", "hudw_big[3][3][3][10]", "hudw_wid_id", "hudw_tiles[%d][8]" % len(a["tiles"]), "hudw_faces[42][16][8]", "HUDW_NTILES", "hudw_bgmap[4][32]"):
        assert needle in h, needle
    # determinism
    b = G.build_assets(G.read_iwad(G.make_iwad(synthetic_lumps())))
    assert G.emit_header(b) == h


def test_model_and_preview():
    a = G.build_assets(G.read_iwad(G.make_iwad(synthetic_lumps())))
    n = len(a["tiles"])
    for st in G.SAMPLE_STATES:
        rows = G.model_rows(a, st)
        assert len(rows) == 4 and all(len(r) == 32 for r in rows)
        assert all(0 <= v < n + 16 for r in rows for v in r)
        L, ids = G.LAYOUT, a["ids"]
        if st["health"] == 63:       # leading zero of the hundreds is transparent: the stone tile stays
            assert rows[0][L["HEALTH_C"]] == a["bgmap"][0][L["HEALTH_C"]]
            assert rows[0][L["HEALTH_C"] + 1] == ids["big"][1][1][0][6]
            assert rows[0][L["HEALTH_C"] + 3] == ids["pct"][0][0]
        if st["ammo_r"] < 0:         # no ammo widget: the background stays
            assert rows[0][L["AMMO_C"]] == a["bgmap"][0][L["AMMO_C"]]
        mask = st["arms"] | (st["keys"] << 6)
        for c in ids["wid"]:         # every ARMS / key cell selects its variant from the owned bits
            v = (mask >> c["b0"] & 1) | ((mask >> c["b1"] & 1) << 1 if c["b1"] != 255 else 0)
            assert rows[c["row"]][c["col"]] == c["ids"][v]
    with tempfile.TemporaryDirectory() as d:
        out, png = os.path.join(d, "h.h"), os.path.join(d, "p.png")
        wad = os.path.join(d, "s.wad")
        open(wad, "wb").write(G.make_iwad(synthetic_lumps()))
        assert G.main(["--wad", wad, "--out", out, "--preview", png]) == 0
        assert open(png, "rb").read(8) == b"\x89PNG\r\n\x1a\n" and os.path.getsize(png) > 200
        assert "hudw_pal" in open(out).read()


def test_missing_lump_reports():
    lumps = [l for l in synthetic_lumps() if l[0] != "STFDEAD0"]
    try:
        G.build_assets(G.read_iwad(G.make_iwad(lumps)))
    except G.WadError as e:
        assert "STFDEAD0" in str(e)
        return
    raise AssertionError("expected WadError")


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f()
    print("PASS test_gen_hud_wad")
