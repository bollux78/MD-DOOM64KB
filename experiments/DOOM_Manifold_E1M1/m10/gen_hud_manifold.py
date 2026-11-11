#!/usr/bin/env python3
"""M10: Claudio's R128 HUD-WAD generator, adapted for Manifold's VRAM budget.

Runs scripts/lab/gen_hud_wad.py unchanged (R128 output is not affected) with one
Manifold-only adjustment: the big-number boxes (AMMO, HEALTH %, ARMOR %) get a
uniform stone tile per row under the digits, so every digit/position shares the
same tile. That cuts the static set from ~389 to ~170 tiles; everything else
(bar, ARMS plate, keys, ammo table, 42 faces, palettes) is the R128 artwork.
"""
import sys, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("gen_hud_wad", ROOT / "scripts/lab/gen_hud_wad.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

_orig_dither = G.fs_dither


def _flatten_number_boxes(bar):
    L = G.LAYOUT
    ref_c = L["HEALTH_C"] + 1                     # the same stone cell the ammo table uses
    for r in range(3):
        ref = [row[ref_c * 8:(ref_c + 1) * 8] for row in bar[r * 8:(r + 1) * 8]]
        for c0 in (L["AMMO_C"], L["HEALTH_C"], L["ARMOR_C"]):
            for c in range(c0, c0 + 4):
                for y in range(8):
                    bar[r * 8 + y][c * 8:(c + 1) * 8] = list(ref[y])
    return bar


def fs_dither(img, pal, mask=None, flat=None, strength=1.0):
    out = _orig_dither(img, pal, mask, flat, strength)
    if mask is None and len(out) == G.ROWS * 8 and len(out[0]) == G.COLS * 8:
        out = _flatten_number_boxes(out)
    return out


G.fs_dither = fs_dither

if __name__ == "__main__":
    sys.exit(G.main(sys.argv[1:]))


# ---------------------------------------------------------------------------
# One CRAM line for the whole bar: Manifold uses PAL0 weapon, PAL1 3D view,
# PAL3 object sprites + text, so the HUD only owns PAL2. Faces are remapped
# into the bar palette: rarely used bar entries give their slot to skin tones.
def single_palette(header_path, free_slots=5):
    import re
    s = open(header_path).read()
    def arr(name):
        m = re.search(name + r"\[16\] = \{([^}]*)\}", s)
        return [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{4})", m.group(1))]
    pal, fpal = arr("hudw_pal"), arr("hudw_fpal")
    rgb = lambda w: ((w >> 1) & 7, (w >> 5) & 7, (w >> 9) & 7)
    d2 = lambda a, b: 2 * (a[0]-b[0])**2 + 4 * (a[1]-b[1])**2 + 3 * (a[2]-b[2])**2
    tm = re.search(r"(hudw_tiles\[\d+\]\[8\] = \{)(.*?)(\};)", s, re.S)
    fm = re.search(r"(hudw_faces\[\d+\]\[16\]\[8\] = \{)(.*?)(\};)", s, re.S)
    words = lambda body: [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{8})", body)]
    tw, fw = words(tm.group(2)), words(fw_ := fm.group(2))
    from collections import Counter
    use = Counter((w >> (4*k)) & 15 for w in tw for k in range(8))
    fuse = Counter((w >> (4*k)) & 15 for w in fw for k in range(8))
    # bar slots to give away: unused / rare ones (never index 0)
    # cost of giving a slot away = pixels using it x error of the nearest other colour
    # (keeps saturated key-card / digit colours that have no substitute)
    def cost(i):
        others = [j for j in range(1, 16) if j != i]
        return use.get(i, 0) * min(d2(rgb(pal[i]), rgb(pal[j])) for j in others) if use.get(i, 0) else -1
    give = sorted(range(1, 16), key=cost)[:free_slots]
    keep = [i for i in range(1, 16) if i not in give]
    barmap = {i: i for i in range(16)}
    for i in give:
        # index 0 (backdrop black) is a valid target: a dark navy must not snap to the key-card blue
        barmap[i] = min([0] + keep, key=lambda j: d2(rgb(pal[i]), (0, 0, 0) if j == 0 else rgb(pal[j])))
    # most used face colours not already well matched by kept bar colours
    fcols = sorted((i for i in range(1, 16) if fuse.get(i, 0)), key=lambda i: -fuse[i] * min(d2(rgb(fpal[i]), rgb(pal[j])) for j in keep))
    newpal = list(pal)
    for slot, fi in zip(give, fcols):
        newpal[slot] = fpal[fi]
    cand = keep + give[:len(fcols)]
    facemap = {0: 0}
    for i in range(1, 16):
        facemap[i] = min(cand, key=lambda j: d2(rgb(fpal[i]), rgb(newpal[j])))
    remap = lambda w, mp: sum(mp[(w >> (4*k)) & 15] << (4*k) for k in range(8))
    def rebuild(body, mp):
        return re.sub(r"0x([0-9A-Fa-f]{8})", lambda m: "0x%08X" % remap(int(m.group(1), 16), mp), body)
    s = s[:tm.start(2)] + rebuild(tm.group(2), barmap) + s[tm.end(2):]
    fm = re.search(r"(hudw_faces\[\d+\]\[16\]\[8\] = \{)(.*?)(\};)", s, re.S)
    s = s[:fm.start(2)] + rebuild(fm.group(2), facemap) + s[fm.end(2):]
    s = re.sub(r"hudw_pal\[16\] = \{[^}]*\}", "hudw_pal[16] = {" + ",".join("0x%04X" % v for v in newpal) + "}", s)
    s = re.sub(r"hudw_fpal\[16\] = \{[^}]*\}", "hudw_fpal[16] = {" + ",".join("0x%04X" % v for v in newpal) + "}", s)
    open(header_path, "w").write(s)
    return newpal
