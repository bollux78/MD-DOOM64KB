#!/usr/bin/env python3
"""R52-AB palette generator for Pair-V: one CRAM palette per plane.

Plane A (even sample columns) uses PAL0, plane B (odd sample columns) uses PAL1.
Colour index 0 of BOTH palettes is the VDP's transparent black (CRAM word 0).
--zero-policy forbid (default): index 0 is never emitted, every pixel is opaque.
--zero-policy allow: index 0 may pair with a colour (shows the black backdrop);
the project's 16-colour VF path already relies on this. Patch idea: Claudio.
Slots 1..15 of each palette are optimised offline so that, for each of the 256
post-COLORMAP Doom colours, one slot in PAL0 (even columns) and one slot in
PAL1 (odd columns) average to the target colour.

Outputs (in --out):
  r52_ab_tables.h    CRAM words, parity maps, composed COLORMAP LUTs
  r52_ab_report.json parameters, slots, metrics per PLAYPAL sub-palette, warnings
  r52_ab_preview.png optional swatches (needs Pillow)

Model limits (read before trusting numbers): CIELAB dE76, mixtures averaged in
linear light ("blend" = neighbouring columns fused, "raw" = no blending).
Neither is a measurement of a real display. The default weights are a proxy
(wall/sprite patches of the project WAD) and NOT pixels shown in DEMO3; use
--hist to supply real counts. Requires numpy; Pillow is optional.
"""
from __future__ import annotations
import argparse, hashlib, json, re, runpy, struct, sys
from pathlib import Path
import numpy as np

SLOTS = 15          # usable slots per palette (index 0 is transparent black)
PRESETS = {         # tau_luma, mu_luma, tau_chroma, mu_chroma
    "free":   (1e9, 0.0, 1e9, 0.0),
    "luma32": (32.0, 0.10, 1e9, 0.0),
    "near25": (32.0, 0.10, 25.0, 0.15),
}

# ---------------------------------------------------------------- colour maths
_M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
_WHITE = np.array([0.95047, 1.0, 1.08883])

def srgb2lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def lin2srgb(l):
    l = np.clip(l, 0.0, 1.0)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * l ** (1 / 2.4) - 0.055) * 255.0

def to_lab(c8):
    xyz = (srgb2lin(c8) @ _M.T) / _WHITE
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

def luma(c8):
    c = np.asarray(c8, float)
    return 0.299 * c[..., 0] + 0.587 * c[..., 1] + 0.114 * c[..., 2]

def avg_rgb(a8, b8):
    return lin2srgb((srgb2lin(a8) + srgb2lin(b8)) / 2.0)

def delta_e(a8, b8):
    return np.sqrt(((to_lab(a8) - to_lab(b8)) ** 2).sum(-1))

# ------------------------------------------------------------------ WAD access
def wad_lumps(data: bytes):
    if data[:4] != b"IWAD":
        raise SystemExit("WAD: expected the project's big-endian IWAD")
    count = struct.unpack_from(">h", data, 4)[0]
    directory = struct.unpack_from(">I", data, 8)[0]
    if not 0 < count < 4096 or directory < 12 or directory + count * 16 > len(data):
        raise SystemExit("WAD: malformed directory")
    out = []
    for i in range(count):
        pos = directory + i * 16
        off = struct.unpack_from(">I", data, pos)[0]
        size = struct.unpack_from(">H", data, pos + 4)[0]
        name = data[pos + 8:pos + 16].split(b"\0", 1)[0].decode("ascii")
        if off + size > len(data):
            raise SystemExit(f"WAD: lump {name} outside file")
        out.append((name, data[off:off + size]))
    return out

def patch_histogram(patch: bytes) -> np.ndarray:
    """Histogram of palette indices of one Doom patch (transparent pixels skipped)."""
    h = np.zeros(256)
    if len(patch) < 16:
        return h
    width, height = struct.unpack_from(">hh", patch, 0)
    if not 0 < width <= 512 or not 0 < height <= 512 or 8 + width * 4 > len(patch):
        return h
    for x in range(width):
        pos = struct.unpack_from(">I", patch, 8 + 4 * x)[0]
        guard = 0
        while pos < len(patch) and patch[pos] != 255 and guard <= height + 8:
            if pos + 4 > len(patch):
                break
            length = patch[pos + 1]
            if pos + length + 4 > len(patch):
                break
            for v in patch[pos + 3:pos + 3 + length]:
                h[v] += 1
            pos += length + 4
            guard += 1
    return h

def proxy_histogram(lumps, wall_weight, levels, uniform_mix, colormap):
    names = [n for n, _ in lumps]
    def span(a, b):
        if a not in names or b not in names:
            raise SystemExit(f"WAD: missing marker {a}/{b}")
        return names.index(a) + 1, names.index(b)
    w0, w1 = span("P_START", "P_END")
    s0, s1 = span("S_START", "S_END")
    hw = sum((patch_histogram(d) for _, d in lumps[w0:w1]), np.zeros(256))
    hs = sum((patch_histogram(d) for _, d in lumps[s0:s1]), np.zeros(256))
    src = wall_weight * hw / max(hw.sum(), 1) + (1 - wall_weight) * hs / max(hs.sum(), 1)
    post = np.zeros(256)
    uni = np.zeros(256)
    for l in levels:
        m = colormap[l * 256:(l + 1) * 256]
        for ci in range(256):
            post[m[ci]] += src[ci]
            uni[m[ci]] += 1
    post /= post.sum()
    uni /= uni.sum()
    return (1 - uniform_mix) * post + uniform_mix * uni

# --------------------------------------------------------------------- roles
def role_sets(cand_rgb):
    lab = to_lab(cand_rgb)
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    hue = (np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) + 360) % 360
    n = len(cand_rgb)
    neutral = [k for k in range(n) if chroma[k] <= 35]
    accent = [k for k in range(n) if chroma[k] > 35]
    warm = [k for k in accent if hue[k] < 110 or hue[k] >= 330]
    cool = [k for k in accent if 110 <= hue[k] < 330]
    return {"any": list(range(n)), "neutral": neutral, "accent": accent, "warm": warm, "cool": cool}

def resolve_role(spec, sets):
    out = []
    for tok in spec.split("+"):
        if tok not in sets:
            raise SystemExit(f"unknown role '{tok}' (use any, neutral, accent, warm, cool joined by +)")
        out += sets[tok]
    return sorted(set(out))

# ------------------------------------------------------------------ optimiser
class Optimiser:
    def __init__(self, targets, weights, cand_rgb, tau_l, mu_l, tau_c, mu_c, allow_zero=False):
        self.allow_zero = allow_zero
        self.TL = to_lab(targets)
        self.W = weights
        self.cand = cand_rgb
        self.tau_l, self.mu_l, self.tau_c, self.mu_c = tau_l, mu_l, tau_c, mu_c

    def evaluate(self, p0, p1):
        zero = np.zeros((1, 3))
        if self.allow_zero:   # index 0 = transparent black may be a pair partner
            A = np.vstack([zero, self.cand[p0]]) if p0 else zero
            B = np.vstack([zero, self.cand[p1]]) if p1 else zero
        else:                 # only opaque slots; black placeholder just while a palette is still empty
            A = self.cand[p0] if p0 else zero
            B = self.cand[p1] if p1 else zero
        avg = avg_rgb(A[:, None, :], B[None, :, :])
        pen = self.mu_l * np.maximum(0, np.abs(luma(A)[:, None] - luma(B)[None, :]) - self.tau_l) ** 2
        if self.mu_c > 0:
            dab = np.sqrt(((to_lab(A)[:, None, :] - to_lab(B)[None, :, :]) ** 2).sum(-1))
            pen = pen + self.mu_c * np.maximum(0, dab - self.tau_c) ** 2
        lab = to_lab(avg)
        cost = np.sqrt(((lab[None] - self.TL[:, None, None, :]) ** 2).sum(-1)) + pen[None]
        flat = cost.reshape(len(self.TL), -1)
        arg = flat.argmin(1)
        return float((flat[np.arange(len(arg)), arg] * self.W).sum()), arg, A.shape[0], B.shape[0]

    def run(self, allow0, allow1, slots, refine, pin=()):
        chosen = (list(pin), list(pin))
        npin = len(pin)
        allow = (allow0, allow1)
        for step in range(2 * slots):
            w = step % 2
            if len(chosen[w]) >= slots:
                continue
            best = (float("inf"), None)
            for k in allow[w]:
                if k in chosen[w]:
                    continue
                t0 = chosen[0] + [k] if w == 0 else chosen[0]
                t1 = chosen[1] + [k] if w == 1 else chosen[1]
                v = self.evaluate(t0, t1)[0]
                if v < best[0] - 1e-12:
                    best = (v, k)
            if best[1] is None:
                raise SystemExit(f"role restriction leaves no candidate for palette {w}")
            chosen[w].append(best[1])
        for _ in range(refine):
            for w in (0, 1):
                L = chosen[w]
                for pos in range(npin, len(L)):
                    cur = self.evaluate(*chosen)[0]
                    keep = L[pos]
                    for k in allow[w]:
                        if k in L:
                            continue
                        old = L[pos]
                        L[pos] = k
                        v = self.evaluate(*chosen)[0]
                        if v < cur - 1e-9:
                            cur, keep = v, k
                        L[pos] = old
                    L[pos] = keep
        return chosen

# ------------------------------------------------------------------ utilities
def parse_c_array(txt, name):
    m = re.search(re.escape(name) + r"\[[^\]]*\](?:\[[^\]]*\])?=\{(.*?)\};", txt, re.S)
    if not m:
        return None
    return [int(x) for x in re.findall(r"-?\d+", m.group(1))]

def c_array(name, values, typ="uint8_t", width=32):
    xs = [str(int(v)) for v in values]
    lines = [",".join(xs[i:i + width]) for i in range(0, len(xs), width)]
    return f"static const {typ} {name}[{len(xs)}]={{\n" + ",\n".join(lines) + "\n};\n"

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="MD-DOOM64KB checkout (scripts/genpal.py, scripts/doom64.wad)")
    ap.add_argument("--out", default="build/r52", help="output directory (never the source tree by default)")
    ap.add_argument("--mode", choices=sorted(PRESETS), default="near25")
    ap.add_argument("--tau-luma", type=float); ap.add_argument("--mu-luma", type=float)
    ap.add_argument("--tau-chroma", type=float); ap.add_argument("--mu-chroma", type=float)
    ap.add_argument("--p0-role", default="any", help="candidates for PAL0: any|neutral|accent|warm|cool joined by +")
    ap.add_argument("--p1-role", default="any", help="candidates for PAL1")
    ap.add_argument("--pin", default="", help="colours kept in BOTH palettes (solid accents): source indices or #rrggbb, comma separated")
    ap.add_argument("--zero-policy", choices=["forbid", "allow"], default="forbid",
                    help="forbid: index 0 is never emitted (all pixels opaque). allow: index 0 (transparent, shows black backdrop) may pair with a colour")
    ap.add_argument("--slots", type=int, default=SLOTS, help="usable slots per palette, max 15")
    ap.add_argument("--refine", type=int, default=1, help="swap-refinement passes")
    ap.add_argument("--levels", default="6-22", help="COLORMAP light levels for the proxy weights, e.g. 6-22")
    ap.add_argument("--wall-weight", type=float, default=0.7)
    ap.add_argument("--uniform-mix", type=float, default=0.35, help="share of uniform-over-colours weight")
    ap.add_argument("--hist", help="JSON list of 256 counts of POST-COLORMAP colours actually drawn (overrides the proxy)")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()
    if not 1 <= args.slots <= SLOTS:
        raise SystemExit("--slots must be 1..15 (index 0 is transparent black)")
    tl, ml, tc, mc = PRESETS[args.mode]
    tl = args.tau_luma if args.tau_luma is not None else tl
    ml = args.mu_luma if args.mu_luma is not None else ml
    tc = args.tau_chroma if args.tau_chroma is not None else tc
    mc = args.mu_chroma if args.mu_chroma is not None else mc

    repo = Path(args.repo).resolve()
    g = runpy.run_path(str(repo / "scripts/genpal.py"))
    raw = g["load_playpal"]()
    SRC = [g["decode_subpal"](raw, i) for i in range(14)]
    to_rgb, to_word = g["gen_to_rgb"], g["gen_color"]
    wad = (repo / "scripts/doom64.wad").read_bytes()
    lumps = wad_lumps(wad)
    colormap = next((d for n, d in lumps if n == "COLORMAP"), None)
    if colormap is None or len(colormap) % 256 or not 32 <= len(colormap) // 256 <= 64:
        raise SystemExit("WAD: missing or unexpected COLORMAP")
    cm = np.frombuffer(colormap, dtype=np.uint8)
    levels_n = len(colormap) // 256

    a, b = (args.levels.split("-") + [args.levels])[:2]
    levels = range(int(a), int(b) + 1)
    if min(levels) < 0 or max(levels) >= levels_n:
        raise SystemExit("--levels outside COLORMAP")
    if args.hist:
        h = np.array(json.loads(Path(args.hist).read_text()), float)
        if h.shape != (256,) or h.sum() <= 0:
            raise SystemExit("--hist must be 256 positive counts")
        W = h / h.sum()
        weights_src = f"file:{args.hist}"
    else:
        W = proxy_histogram(lumps, args.wall_weight, levels, args.uniform_mix, cm)
        weights_src = "proxy:project-WAD wall/sprite patches"

    TGT = np.array(SRC[0], float)       # target colours, normal sub-palette
    # Candidate slot colours: distinct non-black MD words of sub-palette 0.
    # Several source indices can share a word: keep the most used one, since it
    # is the index whose other sub-palette tints are used for CRAM.
    by_word = {}
    for ci in range(256):
        w = to_word(SRC[0][ci])
        if w and (w not in by_word or W[ci] > W[by_word[w]]):
            by_word[w] = ci
    cand_words = sorted(by_word)
    cand_src = [by_word[w] for w in cand_words]
    cand_rgb = np.array([to_rgb(w) for w in cand_words], float)
    sets = role_sets(cand_rgb)
    allow0 = resolve_role(args.p0_role, sets)
    allow1 = resolve_role(args.p1_role, sets)

    pin = []
    for tok in [s.strip() for s in args.pin.split(",") if s.strip()]:
        if tok.startswith("#"):
            rgbv = np.array([int(tok[1:3], 16), int(tok[3:5], 16), int(tok[5:7], 16)], float)
            k = int(np.argmin(delta_e(cand_rgb, rgbv)))
        else:
            wv = to_word(SRC[0][int(tok)])
            if wv == 0:
                raise SystemExit(f"--pin {tok}: black is index 0 and cannot be pinned")
            k = cand_words.index(wv)
        if k not in pin:
            pin.append(k)
    if len(pin) >= args.slots:
        raise SystemExit("--pin leaves no free slot")
    allow0 = sorted(set(allow0) | set(pin)); allow1 = sorted(set(allow1) | set(pin))
    opt = Optimiser(TGT, W, cand_rgb, tl, ml, tc, mc, allow_zero=(args.zero_policy == "allow"))
    p0, p1 = opt.run(allow0, allow1, args.slots, args.refine, pin)
    obj, arg, nA, nB = opt.evaluate(p0, p1)
    assert len(p0) and len(p1), "both palettes require opaque candidates"
    off = 0 if args.zero_policy == "allow" else 1   # forbid: columns of the cost matrix are CRAM slots 1..15
    even = (arg // nB + off).astype(int)  # PAL0 slot for even sample columns (plane A)
    odd = (arg % nB + off).astype(int)    # PAL1 slot for odd sample columns (plane B)
    if args.zero_policy == "forbid":
        assert (even >= 1).all() and (odd >= 1).all(), "index 0 emitted under --zero-policy forbid"

    reps0 = [cand_src[k] for k in p0] + [0] * (SLOTS - len(p0))
    reps1 = [cand_src[k] for k in p1] + [0] * (SLOTS - len(p1))
    def cram(sp, reps, used):
        row = [0]
        for i in range(SLOTS):
            row.append(to_word(SRC[sp][reps[i]]) if i < used else 0)
        return row
    pal0 = [cram(sp, reps0, len(p0)) for sp in range(14)]
    pal1 = [cram(sp, reps1, len(p1)) for sp in range(14)]
    assert all(r[0] == 0 for r in pal0 + pal1) and all(len(r) == 16 for r in pal0 + pal1)

    # Baseline (current R22 16 solid colours) for the report, if present.
    base = base_cram = None
    pal_h = repo / "src/r22_palette.h"
    if pal_h.exists():
        txt = pal_h.read_text()
        base = parse_c_array(txt, "r22_color")
        flat = parse_c_array(txt, "r22_cram")
        if base and flat and len(base) == 256 and len(flat) == 224:
            base_cram = [flat[i * 16:(i + 1) * 16] for i in range(14)]
        else:
            base = None

    report_sub, warnings = [], []
    _c0 = np.array([to_rgb(w) for w in pal0[0]], float); _c1 = np.array([to_rgb(w) for w in pal1[0]], float)
    _lt = to_lab(TGT); _la = to_lab(avg_rgb(_c0[even], _c1[odd]))
    _ct = np.hypot(_lt[:, 1], _lt[:, 2]); _ca = np.hypot(_la[:, 1], _la[:, 2]); _v = _ct > 40
    vivid_sat = float((np.minimum(_ca, _ct) / np.maximum(_ct, 1e-6) * W)[_v].sum() / max(W[_v].sum(), 1e-12))
    vivid_w = float(W[_v].sum())
    for sp in range(14):
        T = np.array(SRC[sp], float)
        c0 = np.array([to_rgb(w) for w in pal0[sp]], float)
        c1 = np.array([to_rgb(w) for w in pal1[sp]], float)
        ra, rb = c0[even], c1[odd]
        blend = avg_rgb(ra, rb)
        e_bl = float((delta_e(T, blend) * W).sum())
        e_raw = float(((delta_e(T, ra) + delta_e(T, rb)) / 2 * W).sum())
        dY = np.abs(luma(ra) - luma(rb))
        row = dict(sub=sp, blend_dE=e_bl, raw_dE=e_raw, mean_luma_diff=float((dY * W).sum()),
                   pct_weight_luma_diff_gt32=float(W[dY > 32].sum()),
                   distinct_pal0=len(set(pal0[sp])), distinct_pal1=len(set(pal1[sp])))
        if base is not None:
            b0 = np.array([to_rgb(w) for w in base_cram[sp]], float)[np.array(base)]
            row["baseline_16_solid_dE"] = float((delta_e(T, b0) * W).sum())
            if e_bl > row["baseline_16_solid_dE"]:
                warnings.append(f"sub-palette {sp}: blended dE {e_bl:.2f} worse than 16-solid baseline "
                                f"{row['baseline_16_solid_dE']:.2f}")
        report_sub.append(row)

    # Composed LUTs: lut[colormap[level][c]] so kernels keep a single lookup.
    comp_even = even[cm]
    comp_odd = odd[cm]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    h = ["/* Generated by scripts/lab/gen_r52_ab.py. Never edit by hand. */",
         "#ifndef DOOM_R52_AB_TABLES_H", "#define DOOM_R52_AB_TABLES_H",
         f"#define R52_COLORMAP_BYTES {len(colormap)}",
         "/* PAL0 = plane A = even sample columns; PAL1 = plane B = odd columns.",
         " * Index 0 of both is transparent black and must stay 0 in every sub-palette. */",
         c_array("r52_pal0", [w for r in pal0 for w in r], "uint16_t", 16),
         c_array("r52_pal1", [w for r in pal1 for w in r], "uint16_t", 16),
         c_array("r52_even", even), c_array("r52_odd", odd),
         c_array("r52_comp_even", comp_even), c_array("r52_comp_odd", comp_odd),
         "#endif"]
    text = "\n".join(h) + "\n"
    (out / "r52_ab_tables.h").write_text(text)

    rep = dict(
        generator="gen_r52_ab.py", header_sha256=hashlib.sha256(text.encode()).hexdigest(),
        args=vars(args), constraints=dict(tau_luma=tl, mu_luma=ml, tau_chroma=tc, mu_chroma=mc),
        weights=weights_src, objective_sub0=obj, pinned=[cand_src[k] for k in pin],
        vivid_saturation_retention_sub0=vivid_sat, vivid_weight=vivid_w,
        palette_slots=dict(
            pal0=[dict(slot=i + 1, src_index=cand_src[k], word=cand_words[k], rgb=[int(v) for v in cand_rgb[k]]) for i, k in enumerate(p0)],
            pal1=[dict(slot=i + 1, src_index=cand_src[k], word=cand_words[k], rgb=[int(v) for v in cand_rgb[k]]) for i, k in enumerate(p1)]),
        parity_maps=dict(even=[int(v) for v in even], odd=[int(v) for v in odd]),
        per_subpalette=report_sub, warnings=warnings,
        distinct_perceived_w_ge_0p1pct_sub0=len({tuple(np.round(avg_rgb(
            np.array([to_rgb(w) for w in pal0[0]], float)[even[c]],
            np.array([to_rgb(w) for w in pal1[0]], float)[odd[c]])).astype(int)) for c in range(256) if W[c] >= 0.001}),
        notes=[f"Index 0 is transparent black in both palettes; zero policy = {args.zero_policy}.",
               "dE is model-based (CIELAB76, linear-light averaging); not a display measurement.",
               "Only sub-palette 0 is optimised; sub-palettes 1..13 reuse the same source indices."])
    (out / "r52_ab_report.json").write_text(json.dumps(rep, indent=1) + "\n")

    if not args.no_preview:
        try:
            from PIL import Image, ImageDraw
            cell = 28
            img = Image.new("RGB", (16 * cell, 16 * cell + 3 * cell), (24, 24, 24))
            d = ImageDraw.Draw(img)
            for i in range(16):
                d.rectangle([i * cell, 0, i * cell + cell - 1, cell - 1], fill=tuple(int(v) for v in to_rgb(pal0[0][i])))
                d.rectangle([i * cell, cell, i * cell + cell - 1, 2 * cell - 1], fill=tuple(int(v) for v in to_rgb(pal1[0][i])))
            c0 = np.array([to_rgb(w) for w in pal0[0]], float)
            c1 = np.array([to_rgb(w) for w in pal1[0]], float)
            for c in range(256):
                x, y = (c % 16) * cell, 3 * cell + (c // 16) * cell
                d.rectangle([x, y, x + cell - 1, y + cell // 2 - 1], fill=tuple(int(v) for v in SRC[0][c]))
                d.rectangle([x, y + cell // 2, x + cell // 2 - 1, y + cell - 1], fill=tuple(int(v) for v in c0[even[c]]))
                d.rectangle([x + cell // 2, y + cell // 2, x + cell - 1, y + cell - 1], fill=tuple(int(v) for v in c1[odd[c]]))
            img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
            img.save(out / "r52_ab_preview.png")
        except ImportError:
            pass

    s0 = report_sub[0]
    print(f"R52-AB {args.mode}: sub0 blend dE {s0['blend_dE']:.2f}, raw dE {s0['raw_dE']:.2f}, "
          f"baseline {s0.get('baseline_16_solid_dE', float('nan')):.2f}, "
          f"distinct {rep['distinct_perceived_w_ge_0p1pct_sub0']}, vivid-sat {vivid_sat:.2f}, warnings {len(warnings)}")
    for w in warnings:
        print("WARNING:", w)

if __name__ == "__main__":
    sys.exit(main())
