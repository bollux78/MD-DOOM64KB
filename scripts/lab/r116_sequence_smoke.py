#!/usr/bin/env python3
"""R116 Run All: verify an automatic E1M8 -> E1M9 transition in BlastEm.

Arms sequence at G_Ticker with E1M8 as current (completed=7), then requests
a controlled demo stop after 256 ticker hits. This deliberately exercises the
safe automatic handoff without relying on the demo's full recording length.
This is a smoke test, NOT a proof that all ten demos finished on hardware.
Checks that AI Normal stays selected even though R116 used to force Normal.
No third-party LMP or ROM is uploaded.
"""
import argparse, importlib.util, json, pathlib, sys


def load_rsp():
    p = pathlib.Path(__file__).with_name("r64a_rsp_capture.py")
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def symbol(syms, name):
    if name in syms:
        return syms[name] & 0xffffff
    matches = [v for k, v in syms.items() if k.startswith(name + ".")]
    if len(matches) != 1:
        raise RuntimeError("ELF symbol unavailable: " + name)
    return matches[0] & 0xffffff


def main():
    ap = argparse.ArgumentParser()
    for name in ("blastem", "rom", "elf", "out"):
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--max-emulated-frames", type=int, default=9950)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    if not (1 <= a.max_emulated_frames <= 10000):
        raise ValueError("frame cap outside permitted range")
    rsp = load_rsp()
    syms = rsp.symbols(a.elf)
    tk = symbol(syms, "G_Ticker")
    err = symbol(syms, "I_Error")
    results = symbol(syms, "I_BenchmarkShowResults")
    handoff_names = [n for n in syms if n == "R116_SequenceContinue" or n.startswith("R116_SequenceContinue.")]
    def get(name):
        return rsp_g.readmem(symbol(syms, name), 1)[0]
    def put(name, val):
        if rsp_g.req("M%x,1:%02x" % (symbol(syms, name), val)) != "OK":
            raise RuntimeError("cannot write " + name)
    record = {"status": "INCONCLUSIVE", "armed": False, "saw_8": False, "saw_9": False, "ticker_hits": 0, "forced_stop": False}
    rsp_g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, a.timeout)
    try:
        rsp_g.req("qSupported")
        record["handoff_symbol_found"] = bool(handoff_names)
        for bp in (tk, err, results):
            if rsp_g.req("Z0,%x,2" % bp) != "OK":
                raise RuntimeError("cannot set breakpoint " + hex(bp))
        while True:
            try:
                rsp_g.cont()
            except (RuntimeError, TimeoutError) as e:
                record["status"] = "INCONCLUSIVE"
                record["reason"] = str(e)
                record["emulator_returncode"] = rsp_g.proc.poll()
                if record["armed"]:
                    record["last_seq_state"] = {
                        "on": get("r116_seq_on"), "active": get("r116_active"),
                        "completed": get("r116_seq_completed"),
                        "pending": get("r116_seq_pending")
                    } if rsp_g.proc.poll() is None else None
                break
            pc = int(rsp_g.req("g")[17 * 8:18 * 8], 16) & 0xffffff
            if pc == err:
                record["status"] = "FAIL_RUNTIME"
                record["reason"] = "I_Error breakpoint"
                break
            if pc == results:
                record["status"] = "FAIL_PREMATURE_RESULTS"
                record["reason"] = "Results screen reached before automatic handoff"
                record["state_at_results"] = {
                    "on": get("r116_seq_on"), "active": get("r116_active"),
                    "completed": get("r116_seq_completed"),
                    "pending": get("r116_seq_pending")
                }
                break
            if pc != tk:
                continue
            record["ticker_hits"] += 1
            if not record["armed"]:
                put("r116_sel", 8)
                put("r116_seq_on", 1)
                put("r116_seq_completed", 7)
                put("r116_seq_pending", 0)
                put("r116_norender", 1)
                put("r89_ai_low", 0)  # Explicitly test user-selected Normal, not Low.
                record["armed"] = True
                continue
            active = get("r116_active")
            if active == 8:
                record["saw_8"] = True
                if record["ticker_hits"] >= 256 and not record["forced_stop"]:
                    # Simulate a demo-ending condition (as on a map exit).
                    # The outer-loop handoff must not run inside G_Ticker.
                    record["state_at_stop"] = {
                        "on": get("r116_seq_on"), "active": active,
                        "completed": get("r116_seq_completed"),
                        "pending": get("r116_seq_pending")
                    }
                    put("r116_stop", 1)
                    record["forced_stop"] = True
            if active == 9:
                record["saw_9"] = True
                record["seq_completed"] = get("r116_seq_completed")
                record["seq_pending"] = get("r116_seq_pending")
                record["ai_mode_low"] = get("r89_ai_low")
                record["status"] = ("PASS_TRANSITION"
                                    if record["saw_8"] and record["forced_stop"] and record["seq_completed"] == 8
                                    and record["seq_pending"] == 0
                                    and record["ai_mode_low"] == 0
                                    else "FAIL_STATE")
                break
    except Exception as e:
        record["status"] = "FAIL_PROBE"
        record["reason"] = str(e)
    finally:
        rsp_g.close()
    pathlib.Path(a.out).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)
    return 0 if record["status"] == "PASS_TRANSITION" else 1


if __name__ == "__main__":
    sys.exit(main())
