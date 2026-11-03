#!/usr/bin/env python3
"""R116: play each per-map test demo in BlastEm (PERF demotest ROM, logic only) and check sync.

One BlastEm run per demo (<= 10,000 emulated frames each, AGENTS.md). Before G_DoPlayDemo executes, the probe writes r116_sel=k and r116_norender=1
(D_Display skipped). At the first G_Ticker it verifies that the selected demo is active.
Stops: R116_Done (first level exit, r116_res filled), R116_End (demo data ended without an exit),
I_Error, or the emulator frame limit.
UV-Max pass: exit leveltime == want +-1, kills == total, secrets == total, exit map == demo map.
Special (want 0): pass = no I_Error and the demo ran to an exit or to its end.
"""
import argparse, importlib.util, json, pathlib, re, struct, sys


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def sym(syms, name):
    if name in syms: return syms[name] & 0xFFFFFF
    m = [v for k, v in syms.items() if k.startswith(name + ".")]
    assert len(m) == 1, (name, m)
    return m[0] & 0xFFFFFF


def table(header):
    rows = re.findall(r'\{"(DTE1M\w+)","([^"]*)",(\d+)u,(\d+)u,(\d+)u\}', pathlib.Path(header).read_text())
    return [None] + [dict(lump=a, label=b, want=int(c), map=int(d), nocap=int(e)) for a, b, c, d, e in rows]


RES = struct.Struct('>iIhhhhhhHHHBBBB2x')
FIELDS = 'exit_time exit_gametic kills tkills items titems secrets tsecrets zmin_total zmin_largest deaths map secretexit sel done'.split()


def run_one(rsp, a, syms, k, d):
    tic_a, lt_a = sym(syms, "_g_gametic"), sym(syms, "_g_leveltime")
    tk, play, done, end, err = (sym(syms, n) for n in ("G_Ticker", "G_DoPlayDemo", "R116_Done", "R116_End", "I_Error"))
    res = {"index": k, "lump": d["lump"], "label": d["label"], "want": d["want"], "map": d["map"], "nocap": d["nocap"]}
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, a.timeout)
    tics = 0; last = {}
    try:
        g.req("qSupported")
        for bp in (tk, play, done, end, err): assert g.req("Z0,%x,2" % bp) == "OK"
        armed = False
        while True:
            try:
                g.cont()
            except (RuntimeError, TimeoutError) as e:
                res["end"] = "frame_limit"; res["emulator"] = str(e); break
            pc = int(g.req("g")[17 * 8:18 * 8], 16) & 0xFFFFFF
            if pc == play:
                assert not armed, "unexpected repeated G_DoPlayDemo entry"
                assert g.req("M%x,1:%02x" % (sym(syms, "r116_sel"), k)) == "OK"
                assert g.req("M%x,1:01" % sym(syms, "r116_norender")) == "OK"
                assert g.req("z0,%x,2" % play) == "OK"
                armed = True
                continue
            if pc == tk:
                assert armed, "G_Ticker ran before G_DoPlayDemo; demo was not selected"
                if tics == 0:
                    selected = int.from_bytes(g.readmem(sym(syms, "r116_active"), 1), "big")
                    assert selected == k, ("demo selection not active", selected, k)
                    res["selected_verified"] = True
                tics += 1
                if tics % 64 == 0:
                    last = {"gametic": int.from_bytes(g.readmem(tic_a, 4), "big"), "leveltime": int.from_bytes(g.readmem(lt_a, 4), "big")}
                continue
            r = dict(zip(FIELDS, RES.unpack(g.readmem(sym(syms, "r116_res"), RES.size))))
            res["res"] = r
            res["end"] = {done: "exit", end: "demo_end_no_exit", err: "i_error"}[pc]
            break
    except Exception as e:
        res["end"] = "probe_error"; res["error"] = str(e)
    finally:
        g.close()
    res["ticks_seen"] = tics; res["last"] = last
    r = res.get("res")
    if d["want"]:
        res["pass"] = bool(res["end"] == "exit" and r and abs(r["exit_time"] - d["want"]) <= 1 and r["kills"] == r["tkills"]
                           and r["secrets"] == r["tsecrets"] and r["map"] == d["map"])
    else:
        res["pass"] = res["end"] in ("exit", "demo_end_no_exit")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True); ap.add_argument("--elf", required=True)
    ap.add_argument("--header", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=""); ap.add_argument("--max-emulated-frames", type=int, default=9800)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args(); assert 1 <= a.max_emulated_frames <= 10000
    rsp = load_rsp(); syms = rsp.symbols(a.elf); T = table(a.header); assert len(T) == 11, len(T)
    ks = [int(x) for x in a.only.split(',')] if a.only else list(range(1, 11))
    out = []
    for k in ks:
        r = run_one(rsp, a, syms, k, T[k]); out.append(r); print(json.dumps(r), flush=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print("R116 SUMMARY", " ".join("%s=%s" % (r["lump"], "PASS" if r["pass"] else "FAIL:" + r["end"]) for r in out))
    return 0 if all(r["pass"] for r in out) else 1


if __name__ == "__main__":
    sys.exit(main())
