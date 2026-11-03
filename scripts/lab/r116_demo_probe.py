#!/usr/bin/env python3
"""R116: bounded BlastEm *safety/stability* stress test for all Episode 1 maps.

DO NOT require vanilla Doom 1.9 demo synchronization, map exit times, kills, secrets,
monster placement, or identical gameplay. Recorded demos are only repeatable stress inputs.
Breakpoints catch I_Error; periodically inspect zone headroom and game-tic progress.
A clean frame-cap exit proves only the *observed window*, never the full demo or physical
Mega Drive hardware. Hardware validation still requires testing on a console.
Outcomes: PASS_COMPLETE, PASS_WINDOW, FAIL_RUNTIME, FAIL_MEMORY, INCONCLUSIVE.
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
    tk, done, end, err = (sym(syms, n) for n in ("G_Ticker", "R116_Done", "R116_End", "I_Error"))
    res = {"index": k, "lump": d["lump"], "label": d["label"], "want": d["want"], "map": d["map"], "nocap": d["nocap"]}
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, a.timeout)
    tics = 0; last = {}; zone_samples = []; tic_samples = []
    try:
        g.req("qSupported")
        for bp in (tk, done, end, err): assert g.req("Z0,%x,2" % bp) == "OK"
        armed = False; verified = False
        def arm():
            assert g.req("M%x,1:%02x" % (sym(syms, "r116_sel"), k)) == "OK"
            assert g.req("M%x,1:01" % sym(syms, "r116_norender")) == "OK"
        while True:
            try:
                g.cont()
            except TimeoutError as e:
                res["end"] = "timeout"; res["emulator"] = str(e); break
            except RuntimeError as e:
                res["emulator"] = str(e)
                # RSP EOF can occur at the intentional -b frame cap or on a crash.
                # Distinguish by process exit status; never call a signal/error exit safe.
                if "RSP EOF" in str(e) or "BlastEm exited before RSP reply" in str(e):
                    try:
                        rc = g.proc.wait(timeout=2)
                    except Exception:
                        rc = g.proc.poll()
                    res["emulator_returncode"] = rc
                    res["end"] = "frame_limit" if rc == 0 else "emulator_error"
                else:
                    res["end"] = "emulator_error"
                break
            pc = int(g.req("g")[17 * 8:18 * 8], 16) & 0xFFFFFF
            if pc == tk:
                if not armed: arm(); armed = True
                elif not verified:
                    selected = int.from_bytes(g.readmem(sym(syms, "r116_active"), 1), "big")
                    assert selected == k, ("demo selection not active", selected, k)
                    res["selected_verified"] = True
                    verified = True
                tics += 1
                if tics % 64 == 0:
                    last = {"gametic": int.from_bytes(g.readmem(tic_a, 4), "big"),
                            "leveltime": int.from_bytes(g.readmem(lt_a, 4), "big")}
                    tic_samples.append(last["gametic"])
                    sample = dict(zip(FIELDS, RES.unpack(g.readmem(sym(syms, "r116_res"), RES.size))))
                    ztotal = sample["zmin_total"]
                    zlargest = sample["zmin_largest"]
                    if ztotal != 65535 and zlargest != 65535:
                        zone_samples.append([ztotal, zlargest])
                        if zlargest > ztotal or ztotal == 0 or zlargest == 0:
                            raise MemoryError("invalid or exhausted zone headroom: " + str([ztotal, zlargest]))
                    # Detect a tic counter that stopped progressing while G_Ticker fires.
                    if len(tic_samples) >= 2 and tic_samples[-1] <= tic_samples[-2]:
                        raise RuntimeError("gametic did not progress over 64 ticker hits")
                    res["last"] = last
                continue
            if pc == err:
                # Reading game structs at the error handler may itself fail.
                res["end"] = "i_error"
                break
            r = dict(zip(FIELDS, RES.unpack(g.readmem(sym(syms, "r116_res"), RES.size))))
            res["res"] = r
            res["end"] = {done: "exit", end: "demo_end_no_exit"}[pc]
            break
    except MemoryError as e:
        res["end"] = "memory_error"; res["error"] = str(e)
    except RuntimeError as e:
        res["end"] = "stall" if "gametic did not progress" in str(e) else "probe_error"
        res["error"] = str(e)
    except Exception as e:
        res["end"] = "probe_error"; res["error"] = str(e)
    finally:
        g.close()
    res["ticks_seen"] = tics
    res["last"] = last
    if zone_samples:
        res["zone_min_total"] = min(z[0] for z in zone_samples)
        res["zone_min_largest"] = min(z[1] for z in zone_samples)
        if res["zone_min_total"] < 1024 or res["zone_min_largest"] < 512:
            res["memory_warning"] = "low zone headroom: investigate before real hardware"
    # No exact Doom 1.9 sync/exit/statistics gate: a different gameplay path is allowed.
    if res["end"] in ("exit", "demo_end_no_exit") and res.get("selected_verified") and zone_samples:
        res["status"] = "PASS_COMPLETE"
    elif res["end"] == "frame_limit" and res.get("selected_verified") and zone_samples and len(tic_samples) > 1:
        res["status"] = "PASS_WINDOW"  # Only the bounded run; never full-demo proof.
    elif res["end"] == "memory_error":
        res["status"] = "FAIL_MEMORY"
    elif res["end"] in ("i_error", "timeout", "emulator_error", "stall"):
        res["status"] = "FAIL_RUNTIME"
    else:
        res["status"] = "INCONCLUSIVE"
    res["pass"] = res["status"] in ("PASS_COMPLETE", "PASS_WINDOW")
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
    print("R116 SAFETY SUMMARY", " ".join("%s=%s" % (r["lump"], r["status"]) for r in out), flush=True)
    return 0 if all(r["pass"] for r in out) else 1


if __name__ == "__main__":
    sys.exit(main())
