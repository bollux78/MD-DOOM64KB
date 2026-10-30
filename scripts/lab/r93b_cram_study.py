#!/usr/bin/env python3
"""R93b (Claudio): SH1 CRAM study, round 2. OFFLINE ONLY: no header consumed by a build is written.

Model (identical to gen_r79_shadow.py, verified exactly against the real r79_shadow_tables.h):
  target[b][c]  = M50 mix of the base R76 slot c and its partner        (what R89/R91-control shows)
  shown[b][s][o]= M50 mix of SH1 CRAM slot o and its partner, x0.5 in shadow (s=1)
  code[b][s][c] = argmin_o Lab error; joint 8x8 state = argmin of summed per-sample costs (R91).
A CRAM change therefore moves every code whose slot OR partner slot changed, the remap and the
joint state. Each candidate is evaluated through that whole pipeline.

Weights: real DEMO3 captures with Shadow On (r93b_capture.py), per mode (A2, L3), from the
pre-pass keys inside the transferred rectangle on p=0 frames. The post-pass capture is used to
check that the replica reproduces the ROM's states and codes.

Search: per mode, coordinate descent over the 30 opaque p=0 slots (512 words each).
A change is accepted only if every guard holds for every (bank, state, input code) that carries
>= GUARD_W of the displayed samples:
  chroma |C-Ct| <= max(6, SH1), hue (Ct>10) <= max(8 deg, SH1), |L-Lt| <= max(6, SH1),
  neutral targets (Ct<8) stay within max(8, SH1) chroma,
and globally: shadow-block share within +-5 points of SH1, mean displayed L within +-1.5,
weighted "beige" share not above SH1. Otherwise the slot is kept; a slot whose codes are flagged
in SH1 and still have no acceptable word is reported as WITHOUT ACCEPTABLE SOLUTION, with the best
guard-violating compromise listed separately (never applied).
p>0 effect rows are not touched (SH1 rounding kept). Proxy: R79 sRGB/Lab, not measured DAC/CRT.
usage: r93b_cram_study.py --tables r59_color_tables.h --r79 r79_shadow_tables.h \
         --cap-a2 DIR --cap-l3 DIR [--werk CRAM-CANDIDATE.json] --out DIR
"""
import argparse, csv, json, re, runpy
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
M = runpy.run_path(str(HERE / "gen_r52_claudio.py"))
avg, to_lab = M["avg_rgb"], M["to_lab"]
GAIN = 1.35
GUARD_W = 0.001
PIX = 3344
MODES = (("A2", "r76_a", 1), ("L3", "r76_l", 2))


def parse(text, name):
    m = re.search(r"\b" + re.escape(name) + r"(?:\[\d+\])+\s*=\s*\{(.*?)\};", text, re.S); assert m, name
    return np.array([int(v, 0) for v in re.findall(r"0x[\da-fA-F]+|\d+", m[1])], int)


def rgb(w):
    w = np.asarray(w); return np.stack([(w >> 1) & 7, (w >> 5) & 7, (w >> 9) & 7], -1) * 255. / 7.


def sh1_words(base):
    c = np.stack([(base >> 1) & 7, (base >> 5) & 7, (base >> 9) & 7], -1)
    b = np.minimum(7, np.floor(c * GAIN + .5)).astype(int)
    return (b[..., 0] << 1) | (b[..., 1] << 5) | (b[..., 2] << 9)


def hue(lab): return np.degrees(np.arctan2(lab[..., 2], lab[..., 1]))
def hdiff(a, b): return np.abs((a - b + 180) % 360 - 180)
def chroma(lab): return np.hypot(lab[..., 1], lab[..., 2])


class Mode:
    def __init__(self, text, prefix):
        self.base = np.array([parse(text, prefix + "_pal" + str(b)).reshape(14, 16) for b in (0, 1)])
        self.part = np.array([parse(text, prefix + "_pairs_" + s).reshape(16, 2)[:, 1] for s in ("even", "odd")])
        tg = np.array([avg(rgb(self.base[b, 0]), rgb(self.base[b, 0])[self.part[b]]) for b in (0, 1)])
        self.tlab = to_lab(tg)                                   # (2,16,3)
        self.tC, self.tH, self.tL = chroma(self.tlab), hue(self.tlab), self.tlab[..., 0]

    def tables(self, words):
        """words (2,16) p=0 CRAM -> code[b,s,c], err (fixed point), shown lab[b,s,o]."""
        sh = []
        for b in (0, 1):
            r = rgb(words[b]); sh.append([avg(r, r[self.part[b]]), avg(r * .5, r[self.part[b]] * .5)])
        slab = to_lab(np.array(sh))                              # (2,2,16,3)
        e = ((self.tlab[:, None, :, None, :] - slab[:, :, None, :, :]) ** 2).sum(-1)   # b,s,c,o
        e[..., 0] = 1e9
        code = np.argmin(e, -1); code[:, :, 0] = 0
        err = np.take_along_axis(e, code[..., None], -1)[..., 0]; err[:, :, 0] = 0
        err = np.minimum(32767, np.floor(err * 4 + .5)).astype(np.int64)
        return code, err, slab


def r79_check(mode, text79, words, mi):
    """Exact equality with the production generator output for p=0."""
    maps = parse(text79, "r79_map"); cost = parse(text79, "r79_cost"); n = maps.size // (14 * 2 * 2 * 256)
    maps = maps.reshape(n, 14, 2, 2, 256); cost = cost.reshape(n, 14, 2, 2, 256)
    if n == 2: mi -= 1          # after gen_r91_shadow.py the header keeps only A2/L3
    code, err, _ = mode.tables(words)
    hi, lo = np.arange(256) >> 4, np.arange(256) & 15
    for s in (0, 1):
        for b in (0, 1):
            assert np.array_equal(maps[mi, 0, s, b] & 255, (code[b, s, hi] << 4) | code[b, s, lo]), ("map", mi, s, b)
            assert np.array_equal(cost[mi, 0, s, b], err[b, s, hi] + err[b, s, lo]), ("cost", mi, s, b)


def load_keys(cap):
    cap = Path(cap)
    recs = [json.loads(l) for l in (cap / "frames.jsonl").read_text().splitlines() if l.strip()]
    pre = np.frombuffer((cap / "pre.bin").read_bytes(), np.uint8).reshape(-1, PIX)
    post = np.frombuffer((cap / "post.bin").read_bytes(), np.uint8).reshape(-1, PIX)
    keys = np.zeros(65536, np.float64); checks = []; p0 = 0
    for i, r in enumerate(recs):
        if r["palette"] != 0 or not r["shadow_on"]: continue
        p0 += 1
        y0, y1, x0, x1 = r["rect"] if r.get("rect") else (3, 20, 3, 36)
        w = pre[i].view(">u2").reshape(22, 76); o = post[i].view(">u2").reshape(22, 76)
        ka = (w[y0:y1, x0:x1] & 255).ravel(); kb = (w[y0:y1, 38 + x0:38 + x1] & 255).ravel()
        np.add.at(keys, (ka.astype(np.int64) << 8) | kb, 1)
        if len(checks) < 400:
            checks.append(((ka.astype(np.int64) << 8) | kb, o[y0:y1, x0:x1].ravel(), o[y0:y1, 38 + x0:38 + x1].ravel()))
    return keys, checks, dict(frames=len(recs), frames_p0_shadow_on=p0, blocks=int(keys.sum()))


class Eval:
    def __init__(self, mode, keys):
        self.m = mode; idx = np.nonzero(keys)[0]
        self.k, self.w = idx, keys[idx]
        self.ka, self.kb = idx >> 8, idx & 255
        self.samp = [(0, self.ka >> 4), (0, self.ka & 15), (1, self.kb >> 4), (1, self.kb & 15)]
        self.nz = ~((self.ka == 0) & (self.kb == 0))

    def run(self, words):
        m = self.m; code, err, slab = m.tables(words)
        cost = lambda s, b, x: err[b, s, x >> 4] + err[b, s, x & 15]
        shadow = (cost(1, 0, self.ka) + cost(1, 1, self.kb)) < (cost(0, 0, self.ka) + cost(0, 1, self.kb))
        st = shadow.astype(int)
        N = np.zeros((2, 2, 16))                                   # displayed samples per bank,state,input code
        for b, c in self.samp: np.add.at(N, (b, st, c), self.w)
        N[:, :, 0] = 0
        shown = slab[np.arange(2)[:, None, None], np.arange(2)[None, :, None], code]   # b,s,c,3
        dC = chroma(shown) - m.tC[:, None, :]
        dH = np.where(m.tC[:, None, :] > 10, hdiff(hue(shown), m.tH[:, None, :]), 0.)
        dL = shown[..., 0] - m.tL[:, None, :]
        dE = np.linalg.norm(shown - m.tlab[:, None], axis=-1)
        yellow = (shown[..., 2] > m.tlab[:, None, :, 2] + 8) & (shown[..., 0] > m.tL[:, None, :] + 6)
        neutral = (m.tC[:, None, :] < 12) & (chroma(shown) > 18) & (shown[..., 2] > 10)
        beige = yellow | neutral
        tot = N.sum()
        f = lambda a: float((N * a).sum() / tot)
        return dict(code=code, err=err, shown=shown, N=N, frac=N / tot, dC=dC, dH=dH, dL=dL, dE=dE, beige=beige,
                    mean_dE=f(dE), mean_absdC=f(np.abs(dC)), mean_dH=f(dH), mean_dL=f(dL), mean_L=f(shown[..., 0]),
                    beige_share=f(beige.astype(float)),
                    shadow_share=float(self.w[self.nz & shadow].sum() / self.w[self.nz].sum()))

    @staticmethod
    def J(r): return r["mean_dE"] + 0.5 * r["mean_absdC"] + 0.2 * r["mean_dH"]


def guards(r, ref):
    """Return list of violated guard names (empty = acceptable)."""
    v = []; live = r["frac"] >= GUARD_W
    ok = lambda a, b: ~live | a
    if not ok(np.abs(r["dC"]) <= np.maximum(6, np.abs(ref["dC"])) + 1e-9, 0).all(): v.append("chroma")
    if not ok(r["dH"] <= np.maximum(8, ref["dH"]) + 1e-9, 0).all(): v.append("hue")
    if not ok(np.abs(r["dL"]) <= np.maximum(6, np.abs(ref["dL"])) + 1e-9, 0).all(): v.append("lightness")
    if abs(r["shadow_share"] - ref["shadow_share"]) > 0.05: v.append("shadow_share")
    if abs(r["mean_L"] - ref["mean_L"]) > 1.5: v.append("mean_L")
    if r["beige_share"] > ref["beige_share"] + 1e-9: v.append("beige_share")
    return v


def neutral_guard(mode, r, ref):
    live = r["frac"] >= GUARD_W; nt = (mode.tC < 8)[:, None, :]
    c, c0 = chroma(r["shown"]), chroma(ref["shown"])
    return bool((~(live & nt) | (c <= np.maximum(8, c0) + 1e-9)).all())


def optimise(mode, ev, w0, sweeps=3):
    ref = ev.run(w0); words = w0.copy(); cur = ref; J0 = Eval.J(ref)
    allw = np.array([(r << 1) | (g << 5) | (b << 9) for r in range(8) for g in range(8) for b in range(8)])
    best_any = {}
    for _ in range(sweeps):
        changed = False
        for b in (0, 1):
            for slot in range(1, 16):
                keep = words[b, slot]; bestJ, bestw = Eval.J(cur), None; anyJ, anyw, anyv = np.inf, None, None
                for w in allw:
                    if w == keep: continue
                    words[b, slot] = w; r = ev.run(words)
                    j = Eval.J(r); v = guards(r, ref)
                    if not neutral_guard(mode, r, ref): v.append("neutral")
                    if not v and j < bestJ - 0.02: bestJ, bestw, bestr = j, w, r
                    if j < anyJ: anyJ, anyw, anyv = j, w, v
                words[b, slot] = keep
                if bestw is not None:
                    words[b, slot] = bestw; cur = bestr; changed = True
                best_any[(b, slot)] = (int(anyw), anyJ, anyv)
        if not changed: break
    return words, ref, cur, best_any, J0


def word_t(w): return tuple(int(x) for x in ((w >> 1) & 7, (w >> 5) & 7, (w >> 9) & 7))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", type=Path, required=True); ap.add_argument("--r79", type=Path, required=True)
    ap.add_argument("--cap-a2", type=Path, required=True); ap.add_argument("--cap-l3", type=Path, required=True)
    ap.add_argument("--werk", type=Path); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sweeps", type=int, default=3)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    text = a.tables.read_text(); text79 = a.r79.read_text()
    werk = json.loads(a.werk.read_text())["palettes"] if a.werk else None
    summary = {"status": "OFFLINE_STUDY_NOT_VISUALLY_VALIDATED", "model": "R79 sRGB/Lab proxy, M50 effective colours; not measured DAC/CRT",
               "weights": "DEMO3 Shadow On captures, p=0 frames, transferred rectangle", "guard_min_sample_share": GUARD_W, "modes": []}
    rows, codes_rows = [], []
    for name, prefix, mi in MODES:
        mode = Mode(text, prefix); w0 = np.array([sh1_words(mode.base[b, 0]) for b in (0, 1)])
        r79_check(mode, text79, w0, mi)
        keys, checks, capinfo = load_keys(a.cap_a2 if name == "A2" else a.cap_l3)
        ev = Eval(mode, keys)
        # replica vs ROM: states and codes of captured frames
        code, err, _ = mode.tables(w0); bad = 0; tot = 0
        for kk, oa, ob in checks:
            ka, kb = kk >> 8, kk & 255
            c = lambda s, bk, x: err[bk, s, x >> 4] + err[bk, s, x & 15]
            sh = (c(1, 0, ka) + c(1, 1, kb)) < (c(0, 0, ka) + c(0, 1, kb))
            st = sh.astype(int)
            pa = (code[0, st, ka >> 4] << 4) | code[0, st, ka & 15]; pb = (code[1, st, kb >> 4] << 4) | code[1, st, kb & 15]
            bad += int(((oa & 255) != pa).sum() + ((ob & 255) != pb).sum() + (((oa >> 15) & 1) != (1 - st)).sum()); tot += len(ka)
        words, ref, cur, best_any, J0 = optimise(mode, ev, w0, a.sweeps)
        cand_w = None
        if werk:
            cand_w = np.array([np.array(werk[mi - 1][b][0]) for b in (0, 1)])
            rw = ev.run(cand_w)
        def met(r): return {k: round(r[k], 4) for k in ("mean_dE", "mean_absdC", "mean_dH", "mean_dL", "mean_L", "beige_share", "shadow_share")}
        entry = {"mode": name, "capture": capinfo, "replica_mismatches": bad, "replica_samples": tot,
                 "sh1": met(ref), "round2": met(cur), "J_sh1": round(J0, 4), "J_round2": round(Eval.J(cur), 4)}
        if werk: entry["werk_r93"] = met(rw); entry["werk_r93_guard_violations"] = guards(rw, ref) + ([] if neutral_guard(mode, rw, ref) else ["neutral"])
        changed = [(b, s) for b in (0, 1) for s in range(16) if words[b, s] != w0[b, s]]
        entry["slots_changed"] = [{"bank": b, "slot": s, "sh1": word_t(w0[b, s]), "round2": word_t(words[b, s])} for b, s in changed]
        # flagged slots in SH1: any live code using the slot (directly or as partner) beige or chroma off by >6
        flag = (ref["frac"] >= GUARD_W) & (ref["beige"] | (np.abs(ref["dC"]) > 6))
        no_sol = []
        for b in (0, 1):
            for s in range(1, 16):
                users = [c for c in range(1, 16) if c == s or mode.part[b][c] == s]
                fl = [c for c in users if flag[b, :, c].any()]
                ideal = to_lab(np.minimum(255, rgb(mode.base[b, 0, s]) * GAIN)); idealS = to_lab(np.minimum(255, rgb(mode.base[b, 0, s]) * GAIN) * .5)
                status = "changed" if (b, s) in changed else ("no_acceptable_solution" if fl else "kept")
                if status == "no_acceptable_solution":
                    aw, aj, av = best_any[(b, s)]
                    no_sol.append({"bank": b, "slot": s, "flagged_codes": fl, "best_compromise": word_t(aw), "compromise_J": round(float(aj), 3), "violates": av})
                rows.append({"mode": name, "bank": b, "slot": s, "base": word_t(mode.base[b, 0, s]), "sh1": word_t(w0[b, s]),
                             "round2": word_t(words[b, s]), "werk_r93": word_t(cand_w[b, s]) if cand_w is not None else "",
                             "status": status, "ideal_chroma_normal": round(float(chroma(ideal)), 1), "ideal_chroma_shadow": round(float(chroma(idealS)), 1),
                             "codes_using_slot": " ".join(map(str, users)), "flagged_codes_sh1": " ".join(map(str, fl))})
        entry["no_acceptable_solution"] = no_sol
        for b in (0, 1):
            for s_ in (0, 1):
                for c in range(1, 16):
                    if ref["frac"][b, s_, c] < GUARD_W and cur["frac"][b, s_, c] < GUARD_W: continue
                    d = lambda r: (round(float(r["shown"][b, s_, c, 0]), 1), round(float(chroma(r["shown"][b, s_, c])), 1), round(float(hue(r["shown"][b, s_, c])), 1))
                    codes_rows.append({"mode": name, "bank": b, "state": ("normal", "shadow")[s_], "input_code": c, "partner": int(mode.part[b][c]),
                                       "share_sh1": round(float(ref["frac"][b, s_, c]), 4), "share_round2": round(float(cur["frac"][b, s_, c]), 4),
                                       "target_LCh": (round(float(mode.tL[b, c]), 1), round(float(mode.tC[b, c]), 1), round(float(mode.tH[b, c]), 1)),
                                       "sh1_LCh": d(ref), "round2_LCh": d(cur), "sh1_beige": bool(ref["beige"][b, s_, c]), "round2_beige": bool(cur["beige"][b, s_, c])})
        summary["modes"].append(entry); print(json.dumps(entry)[:1500], flush=True)
    with (a.out / "SLOTS.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (a.out / "CODES.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(codes_rows[0])); w.writeheader(); w.writerows(codes_rows)
    (a.out / "SUMMARY.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
