#!/usr/bin/env python3
"""R114: run the zone-survey diag PERF ROM in BlastEm until R114_Done, read the per-map minima."""
import argparse, importlib.util, json, pathlib, sys


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True); ap.add_argument("--elf", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--max-emulated-frames", type=int, default=9800)
    a = ap.parse_args(); assert a.max_emulated_frames <= 10000
    rsp = load_rsp(); syms = rsp.symbols(a.elf)
    done = syms["R114_Done"] & 0xFFFFFF
    initnew = [v for k, v in syms.items() if k == "G_InitNew" or k.startswith("G_InitNew.")]
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, 900)
    res = {"rom": a.rom, "snapshots": []}
    def snap(tag):
        tot = g.readmem(syms["r114_min_total"] & 0xFFFFFF, 18); lar = g.readmem(syms["r114_min_largest"] & 0xFFFFFF, 18)
        mp = int.from_bytes(g.readmem(syms["_g_gamemap"] & 0xFFFFFF, 2), "big")
        res["maps"] = [dict(map="E1M%d" % (i + 1), min_total_free=int.from_bytes(tot[2*i:2*i+2], "big"),
                            min_largest_free=int.from_bytes(lar[2*i:2*i+2], "big")) for i in range(9)]
        res["snapshots"].append([tag, mp]); res["last_map"] = mp
    try:
        g.req("qSupported"); assert g.req("Z0,%x,2" % done) == "OK"
        for v in initnew: assert g.req("Z0,%x,2" % (v & 0xFFFFFF)) == "OK"
        while True:
            try:
                g.cont()
            except (RuntimeError, TimeoutError) as e:
                res["end"] = "emulator: %s" % e; break
            pc = int(g.req("g")[17 * 8:18 * 8], 16) & 0xFFFFFF
            snap("done" if pc == done else "initnew")
            if pc == done: res["end"] = "done"; break
        res["framebuffer_bytes"] = 3352
    except Exception as e:
        res["error"] = str(e)
    finally:
        g.close()
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res))


if __name__ == "__main__":
    sys.exit(main())
