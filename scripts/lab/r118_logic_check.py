#!/usr/bin/env python3
"""R118: game-logic fingerprints of one R116 demo, logic only (r116_norender=1), for an exact A/B.

One BlastEm process (<= 10,000 emulated frames). Breakpoint on G_Ticker; every --every tics (and at
R116_Done / R116_End) it records a fingerprint of the game state:
  gametic, leveltime, P_Random indices (rndindex/prndindex when the symbols exist),
  every mobj thinker (function == P_MobjThinker): x, y, z (mobj bytes 12..23) in list order -> sha1,
  the thinker count, the player mobj x/y/z.
Only RAM data is read (no ROM pointers), so builds with different code layout but identical logic give
identical fingerprints. Compare runs with --compare A.json B.json ...: all checkpoints present in every
run must be equal (a faster build reaches more checkpoints in the same frame budget).
"""
import argparse, hashlib, importlib.util, json, pathlib, sys


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def compare(paths):
    runs = [json.loads(pathlib.Path(p).read_text()) for p in paths]
    base = {c["tic"]: c for c in runs[0]["checkpoints"]}; ok = True; rows = []
    for p, r in zip(paths[1:], runs[1:]):
        other = {c["tic"]: c for c in r["checkpoints"]}
        common = sorted(set(base) & set(other))
        bad = [t for t in common if {k: v for k, v in base[t].items()} != {k: v for k, v in other[t].items()}]
        rows.append({"run": p, "common_checkpoints": len(common), "last_common_tic": common[-1] if common else None,
                     "first_mismatch_tic": bad[0] if bad else None})
        ok = ok and not bad and len(common) >= 2
    print(json.dumps(rows, indent=1)); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", nargs="+")
    ap.add_argument("--blastem"); ap.add_argument("--rom"); ap.add_argument("--elf"); ap.add_argument("--out")
    ap.add_argument("--demo", type=int); ap.add_argument("--every", type=int, default=100)
    ap.add_argument("--max-emulated-frames", type=int, default=9800); ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    if a.compare: return compare(a.compare)
    assert 1 <= a.max_emulated_frames <= 10000 and 1 <= a.demo <= 10
    rsp = load_rsp(); syms = rsp.symbols(a.elf)
    def sym(n, need=True):
        if n in syms: return syms[n] & 0xFFFFFF
        m = [v for k, v in syms.items() if k.startswith(n + ".")]
        if len(m) == 1: return m[0] & 0xFFFFFF
        assert not need, (n, m); return None
    be = lambda b: int.from_bytes(b, "big")
    tk, done, end, err = sym("G_Ticker"), sym("R116_Done"), sym("R116_End"), sym("I_Error")
    tic_a, lt_a, cap, pl = sym("_g_gametic"), sym("_g_leveltime"), sym("_g_thinkerclasscap"), sym("_g_player")
    mobjthink = sym("P_MobjThinker")
    rnd = [x for x in (sym("rndindex", False), sym("prndindex", False)) if x is not None]
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, a.timeout)
    res = {"rom": a.rom, "demo": a.demo, "every": a.every, "rng_symbols": len(rnd), "checkpoints": []}
    def fingerprint():
        t = be(g.readmem(tic_a, 4))
        h = hashlib.sha1(); n = 0; node = be(g.readmem(cap + 4, 4)) & 0xFFFFFF
        while node and node != cap and n < 2000:
            hdr = g.readmem(node, 24)
            if (be(hdr[8:12]) & 0xFFFFFF) == mobjthink: h.update(hdr[12:24])
            node = be(hdr[4:8]) & 0xFFFFFF; n += 1
        mo = be(g.readmem(pl, 4)) & 0xFFFFFF
        return {"tic": t, "leveltime": be(g.readmem(lt_a, 4)), "rng": [g.readmem(x, 1)[0] for x in rnd],
                "thinkers": n, "mobj_xyz_sha1": h.hexdigest()[:16], "player_xyz": g.readmem(mo + 12, 12).hex() if mo else None}
    try:
        g.req("qSupported")
        for bp in (tk, done, end, err): assert g.req("Z0,%x,2" % bp) == "OK"
        armed = False; tics = 0
        while True:
            try:
                g.cont()
            except TimeoutError:
                res["end"] = "timeout"; break
            except RuntimeError:
                res["end"] = "frame_limit"; break
            pc = int(g.req("g")[17 * 8:18 * 8], 16) & 0xFFFFFF
            if pc == tk:
                if not armed:
                    assert g.req("M%x,1:%02x" % (sym("r116_sel"), a.demo)) == "OK"
                    assert g.req("M%x,1:01" % sym("r116_norender")) == "OK"; armed = True
                tics += 1
                if tics % a.every == 0: res["checkpoints"].append(fingerprint())
                continue
            res["end"] = {done: "exit", end: "demo_end", err: "i_error"}[pc]
            if pc != err: res["checkpoints"].append(fingerprint())
            break
    except Exception as e:
        res["end"] = "probe_error: %s" % e
    finally:
        g.close()
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("demo", "end", "rng_symbols")}), "checkpoints", len(res["checkpoints"]))
    return 0 if res["end"] in ("frame_limit", "exit", "demo_end") and res["checkpoints"] else 1


if __name__ == "__main__":
    sys.exit(main())
