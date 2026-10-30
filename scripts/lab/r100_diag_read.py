#!/usr/bin/env python3
"""R100: read the per-column diagnostic counters (r100_diag) of an R100 diag PERF ROM during DEMO3.
Breaks on I_FinishUpdate, reads the counters every frame (last value kept), stops at --stop-tic or when
the emulator ends (<= 10,000 emulated frames). Read-only."""
import argparse, importlib.util, json, pathlib
FIELDS = ("cols", "mid_cols", "mid_wall", "r60", "r96_single", "r96_fallback", "r96_empty", "two_cols")
def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
ap = argparse.ArgumentParser()
ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True); ap.add_argument("--elf", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--max-emulated-frames", type=int, default=9000); ap.add_argument("--stop-tic", type=int, default=100000)
a = ap.parse_args(); assert a.max_emulated_frames <= 10000
rsp = load_rsp(); syms = rsp.symbols(a.elf)
def sym(n):
    if n in syms: return syms[n]
    m = [v for k, v in syms.items() if k.startswith(n + ".")]; assert len(m) == 1, (n, m); return m[0]
g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, 300)
last, tic, status = None, 0, "max"
try:
    g.req("qSupported"); assert g.req("Z0,%x,2" % (sym("I_FinishUpdate") & 0xFFFFFF)) == "OK"
    while True:
        try: g.cont()
        except (RuntimeError, TimeoutError) as e: status = "emulator_ended: " + str(e)[:60]; break
        tic = int.from_bytes(g.readmem(sym("_g_gametic"), 4), "big")
        raw = g.readmem(sym("r100_diag"), 4 * len(FIELDS))
        last = {k: int.from_bytes(raw[4 * i:4 * i + 4], "big") for i, k in enumerate(FIELDS)}; last["tic"] = tic
        if tic >= a.stop_tic: status = "stop_tic"; break
finally:
    g.close()
r = dict(last or {}, status=status)
if last and last["cols"]:
    r["share_mid_cols"] = round(last["mid_cols"] / last["cols"], 4)
    r["share_two_cols"] = round(last["two_cols"] / last["cols"], 4)
    r["share_mid_wall_of_cols"] = round(last["mid_wall"] / last["cols"], 4)
    w = last["r60"] + last["r96_single"] + last["r96_fallback"]
    r["wall_calls"] = w
    if w: r["share_fallback_of_wall_calls"] = round(last["r96_fallback"] / w, 4)
pathlib.Path(a.out).write_text(json.dumps(r, indent=1) + "\n"); print(json.dumps(r))
