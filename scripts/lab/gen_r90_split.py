#!/usr/bin/env python3
"""R90-split: bottom-half CRAM (PAL2/PAL3) and LUTs for every R89 colour mode.

Runs inside the build (after gen_r77_profiles.py) on the generated src/r59_color_tables.h.
Top half of the 3D view keeps R89 exactly (PAL0/PAL1, R89 LUTs). Rows >= R90_SPLIT_ROW use
PAL2/PAL3 through static attribute bits and the tables written here.

Constraints of the hardware path: the pair tiles in VRAM are shared, so a code n of the bottom
half still shows the M50 mix of slot n and slot partner(n) of the SAME pairs tables as the top.
Only the colours of the 15+15 slots and the LUTs differ.

Per mode, starting from a copy of the top palettes (= R89 appearance), a coordinate descent swaps
slot colours (candidates: Doom palette colours, so PLAYPAL tints exist for every slot) when that
lowers the bottom-region objective. Guards learnt from the R90 flat rounds, applied per colour:
  - never light grey unless Doom's colour is light grey;
  - lightness within max(R89 |dL|, 8) of Doom's colour; chroma >= min(R89 chroma, 0.7 x Doom's);
  - strong penalty for any colour shown worse than R89 by more than 1 dE (all 256 colours count);
  - wall colours pay mu x dE(bottom, top) so a wall crossing the split does not show a seam;
  - even/odd column contrast term (walls lw, floors lf).
Output: src/r90_split_tables.h and src/r90_split_report.json.
usage: gen_r90_split.py [--wad scripts/doom1.wad] [--src src]
"""
import argparse, importlib.util, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("r90a", ROOT / "scripts/lab/r90_color_analysis.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

SPLIT_ROW = 22                    # sample row (tile row 11): first row drawn with PAL2/PAL3
SHARE_BOTTOM = {"walls": 0.5, "sprites": 0.8, "floors": 1.0}
LAM_W, LAM_F, MU, REG = 0.15, 1.0, 0.3, 20.0
DAC = A.DAC["LIN"]                # R89's palettes were designed with this model; keep it for continuity


def dist(a, b):
    return np.sqrt(((a - b) ** 2).sum(-1))


class Bottom:
    def __init__(self, md, pal8, Hw, Hf):
        self.md, self.pal8 = md, pal8
        s = Hw.sum() + Hf.sum()
        self.Hw, self.Hf = Hw / s, Hf / s
        self.tgt = A.to_lab(pal8); self.tl = self.tgt[:, 0]; self.tch = np.hypot(self.tgt[:, 1], self.tgt[:, 2])
        self.grey_t = (self.tl > 55) & (self.tch < 12)
        self.pe = np.array(md["pairs_even"])[:, 1]; self.po = np.array(md["pairs_odd"])[:, 1]
        E, O = self.codes(md["pal0"], self.pe), self.codes(md["pal1"], self.po)
        self.top_w = A.lab_from_lin((E[md["wall_even"]] + O[md["wall_odd"]]) / 2)
        self.top_f = A.lab_from_lin((E[md["flat_even"]] + O[md["flat_odd"]]) / 2)
        self.etop_w = dist(self.top_w, self.tgt); self.etop_f = dist(self.top_f, self.tgt)
        self.dl_w = np.maximum(np.abs(self.top_w[:, 0] - self.tl), 8.0); self.dl_f = np.maximum(np.abs(self.top_f[:, 0] - self.tl), 8.0)
        chw = np.hypot(self.top_w[:, 1], self.top_w[:, 2]); chf = np.hypot(self.top_f[:, 1], self.top_f[:, 2])
        self.chmin_w = np.where(self.tch > 10, np.minimum(chw, 0.7 * self.tch), 0.0)
        self.chmin_f = np.where(self.tch > 10, np.minimum(chf, 0.7 * self.tch), 0.0)

    @staticmethod
    def codes(words, partner):
        lin = A.srgb2lin(A.word_rgb(np.asarray(words), DAC))
        return (lin + lin[partner]) / 2

    def evaluate(self, w2, w3):
        E = self.codes(w2, self.pe)[1:]; O = self.codes(w3, self.po)[1:]          # codes 1..15 only
        mix = A.lab_from_lin((E[:, None] + O[None]) / 2).reshape(225, 3)
        con = dist(A.lab_from_lin(E)[:, None], A.lab_from_lin(O)[None]).reshape(225)
        ml = mix[:, 0]; mch = np.hypot(mix[:, 1], mix[:, 2]); grey_m = (ml > 55) & (mch < 12)
        err = dist(mix[None], self.tgt[:, None])                                    # 256 x 225
        base = ~(grey_m[None] & ~self.grey_t[:, None])
        dlm = np.abs(ml[None] - self.tl[:, None])
        ok_w = base & (dlm <= self.dl_w[:, None]) & (mch[None] >= self.chmin_w[:, None])
        ok_f = base & (dlm <= self.dl_f[:, None]) & (mch[None] >= self.chmin_f[:, None])
        cw = err + LAM_W * con[None] + MU * dist(mix[None], self.top_w[:, None])
        cf = err + LAM_F * con[None]
        cw = np.where(ok_w, cw, np.inf); cf = np.where(ok_f, cf, np.inf)
        bw = np.argmin(cw, 1); bf = np.argmin(cf, 1)
        fb_w = ~np.isfinite(cw[np.arange(256), bw]); fb_f = ~np.isfinite(cf[np.arange(256), bf])
        bw = np.where(fb_w, np.argmin(err, 1), bw); bf = np.where(fb_f, np.argmin(err, 1), bf)   # no allowed pair: plain nearest
        ew = err[np.arange(256), bw]; ef = err[np.arange(256), bf]
        cwv = np.where(fb_w, ew + 50, cw[np.arange(256), bw]); cfv = np.where(fb_f, ef + 50, cf[np.arange(256), bf])
        reg = np.maximum(0, ew - self.etop_w - 1).sum() + np.maximum(0, ef - self.etop_f - 1).sum()
        obj = float((self.Hw * cwv).sum() + (self.Hf * cfv).sum() + REG / 256.0 * reg)
        stats = dict(regress_w=int((ew > self.etop_w + 1).sum()), regress_f=int((ef > self.etop_f + 1).sum()),
                     fallback=int(fb_w.sum() + fb_f.sum()),
                     grey_new=int((grey_m[bw] & ~self.grey_t).sum() + (grey_m[bf] & ~self.grey_t).sum()),
                     mean_err_w=float((self.Hw * ew).sum() / max(self.Hw.sum(), 1e-12)),
                     mean_err_f=float((self.Hf * ef).sum() / max(self.Hf.sum(), 1e-12)))
        return obj, bw, bf, stats

    def optimise(self, cand, sweeps=2):
        w2 = np.array(self.md["pal0"]).copy(); w3 = np.array(self.md["pal1"]).copy()
        src2 = [None] * 16; src3 = [None] * 16          # None = slot copied from R89 (tint rows copied too)
        best, *_ = self.evaluate(w2, w3); start = best
        for _ in range(sweeps):
            improved = False
            for plane in (2, 3):
                w, src = (w2, src2) if plane == 2 else (w3, src3)
                for slot in range(1, 16):
                    keep = (w[slot], src[slot])
                    for word, idx in cand:
                        if word == w[slot]: continue
                        w[slot] = word
                        o = self.evaluate(w2, w3)[0]
                        if o < best - 1e-6: best, keep, improved = o, (word, idx), True
                    w[slot], src[slot] = keep
            if not improved: break
        return w2, w3, src2, src3, start, best


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--wad", default=str(ROOT / "scripts/doom1.wad")); ap.add_argument("--src", default=str(ROOT / "src"))
    a = ap.parse_args(); src = Path(a.src); t0 = time.time()
    w = A.Wad(a.wad)
    pp = np.frombuffer(w.lump("PLAYPAL"), np.uint8)[:14 * 768].reshape(14, 256, 3).astype(float)
    pal8 = pp[0]
    cm = np.frombuffer(w.lump("COLORMAP"), np.uint8)[:34 * 256].reshape(34, 256)
    tex = A.texture_hists(w); frep = A.flat_rep(w, pal8); spr = {}
    Hw = np.zeros(256); Hf = np.zeros(256)
    for m in A.MAPS:
        _, _, cats = A.map_weights(w, m, tex, frep, spr)
        Hw += SHARE_BOTTOM["walls"] * A.post(cm, cats["walls"]) + SHARE_BOTTOM["sprites"] * A.post(cm, cats["sprites"])
        Hf += SHARE_BOTTOM["floors"] * A.post(cm, cats["floors"])
    print("R90 split weights %.0fs" % (time.time() - t0), flush=True)
    generate(src, pp, cm, Hw, Hf, t0)


def generate(src, pp, cm, Hw, Hf, t0=None, sweeps=2, cand_limit=None):
    t0 = t0 or time.time(); pal8 = pp[0]
    header = src / "r59_color_tables.h"
    modes = A.parse_tables(header)
    by_word = {}
    for i in range(256):
        wd = A.word_of(pal8[i])
        if wd and (wd not in by_word or Hw[i] + Hf[i] > Hw[by_word[wd]] + Hf[by_word[wd]]): by_word[wd] = i
    cand = sorted(by_word.items())[:cand_limit]
    # rows of the R89 top CRAM (14 tints) are needed for slots that stay as copies
    import re
    txt = header.read_text()
    def rows(name):
        m = re.search(r"\b" + re.escape(name) + r"\[14\]\[16\]=\{(.*?)\};", txt, re.S)
        v = np.array([int(x) for x in re.findall(r"\d+", m.group(1))]); assert v.size == 224, name
        return v.reshape(14, 16)
    out = ["/* Generated by gen_r90_split.py: bottom half (PAL2/PAL3) of the R90 split view. Never edit by hand. */",
           "#ifndef R90_SPLIT_TABLES_H", "#define R90_SPLIT_TABLES_H", "#ifndef R59_COLOR_TABLES_H",
           "#error include r59_color_tables.h first", "#endif", "#define R90_SPLIT_ROW %d" % SPLIT_ROW]
    rep = {"split_row": SPLIT_ROW, "weights": SHARE_BOTTOM, "lam_w": LAM_W, "lam_f": LAM_F, "mu": MU, "dac": "LIN", "modes": []}
    inits = []
    for k, md in enumerate(modes):
        b = Bottom(md, pal8, Hw, Hf)
        w2, w3, s2, s3, start, best = b.optimise(cand, sweeps)
        obj, bw, bf, st = b.evaluate(w2, w3)
        ev = (bw // 15 + 1).astype(int); od = (bw % 15 + 1).astype(int)
        fe = (bf // 15 + 1).astype(int); fo = (bf % 15 + 1).astype(int)
        top0, top1 = rows(md["names"][0]), rows(md["names"][1])
        def cram(top, srcs):
            r = top.copy()
            for slot, idx in enumerate(srcs):
                if idx is not None:
                    for sp in range(14): r[sp, slot] = A.word_of(pp[sp][idx])
            assert (r[:, 0] == 0).all()
            return r
        p2, p3 = cram(top0, s2), cram(top1, s3)
        nm = "r90_b%d" % k
        arr = lambda n, v: "static const uint8_t %s[256]={%s};" % (n, ",".join(map(str, v)))
        out.append("static const uint16_t %s_pal0[14][16]={%s};" % (nm, ",".join("{" + ",".join(map(str, r)) + "}" for r in p2)))
        out.append("static const uint16_t %s_pal1[14][16]={%s};" % (nm, ",".join("{" + ",".join(map(str, r)) + "}" for r in p3)))
        out += [arr(nm + "_wall_even", ev), arr(nm + "_wall_odd", od), arr(nm + "_flat_even", fe), arr(nm + "_flat_odd", fo)]
        for par, codes in (("even", ev), ("odd", od)):
            out.append("static const uint8_t %s_comp_%s[34][256]={%s};" % (nm, par, ",".join("{" + ",".join(map(str, codes[cm[l]])) + "}" for l in range(34))))
        f = md["names"]
        inits.append(" {%s_pal0,%s_pal1,%s,%s,%s_wall_even,%s_wall_odd,%s_flat_even,%s_flat_odd,%s_comp_even,%s_comp_odd}," % (nm, nm, f[2], f[3], nm, nm, nm, nm, nm, nm))
        st.update(mode=k, top_name=f[0], replaced_slots=int(sum(x is not None for x in s2) + sum(x is not None for x in s3)),
                  objective_start=start, objective_final=best,
                  top_mean_err_w=float((b.Hw * b.etop_w).sum() / max(b.Hw.sum(), 1e-12)),
                  top_mean_err_f=float((b.Hf * b.etop_f).sum() / max(b.Hf.sum(), 1e-12)))
        rep["modes"].append(st)
        print("R90 split mode %d: slots %d, walls %.1f->%.1f, floors %.1f->%.1f, regressions %d/%d, grey %d, fallback %d (%.0fs)" % (
            k, st["replaced_slots"], st["top_mean_err_w"], st["mean_err_w"], st["top_mean_err_f"], st["mean_err_f"],
            st["regress_w"], st["regress_f"], st["grey_new"], st["fallback"], time.time() - t0), flush=True)
    out.append("static const R59ColorTables r90_bottom_tables[R59_COLOR_MODES]={")
    out += inits
    out += ["};", "#endif"]
    assert len(inits) == len(modes)
    (src / "r90_split_tables.h").write_text("\n".join(out) + "\n")
    (src / "r90_split_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print("R90 split tables written (%.0fs)" % (time.time() - t0))


if __name__ == "__main__":
    sys.exit(main())
