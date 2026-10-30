#!/usr/bin/env python3
"""R94 (Claudio): statistical PC profiler for an unmodified PERF ROM in BlastEm (GDB RSP over stdio).

The emulator runs freely; the host interrupts it (0x03) at random wall-clock intervals, reads PC and
the long word at SP (return address, to attribute leaf helpers), and continues. Samples are taken only
while DEMO3 is running (gametic advancing). Optional one-time RAM writes at the first stop
(--shadow 0/1, --mode 1/2). <= 10,000 emulated frames per BlastEm process (AGENTS.md).
Not a hardware measurement: wall-clock sampling of an emulator; relative shares only.
Writes OUT/samples.tsv, OUT/PROFILE.json, OUT/PROFILE.txt.
"""
import argparse, bisect, collections, importlib.util, json, os, pathlib, random, subprocess, sys, time


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def text_symbols(elf):
    nm = os.environ.get("M68K_NM") or str(pathlib.Path.home() / "mars/m68k-elf/bin/m68k-elf-nm")
    out = subprocess.run([nm, "-n", "-S", "--defined-only", str(elf)], check=True, capture_output=True, text=True).stdout
    syms = []
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 3 and p[-2] in "tTwW":
            syms.append((int(p[0], 16), p[-1]))
    syms.sort(); return syms


def find(syms, addrs, pc):
    i = bisect.bisect_right(addrs, pc) - 1
    return syms[i][1] if i >= 0 else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True); ap.add_argument("--elf", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--shadow", type=int, choices=(0, 1))
    ap.add_argument("--mode", type=int, choices=(1, 2)); ap.add_argument("--max-emulated-frames", type=int, default=9000)
    ap.add_argument("--interval-ms", type=float, default=6.0); ap.add_argument("--max-samples", type=int, default=60000)
    ap.add_argument("--seed", type=int, default=94)
    a = ap.parse_args(); assert 1 <= a.max_emulated_frames <= 10000
    rsp = load_rsp(); allsyms = rsp.symbols(a.elf)
    def sym(n):
        if n in allsyms: return allsyms[n]
        m = [v for k, v in allsyms.items() if k.startswith(n + ".")]; assert len(m) == 1, (n, m); return m[0]
    tic_a = sym("_g_gametic")
    text = text_symbols(a.elf); addrs = [s[0] for s in text]
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=False)
    rng = random.Random(a.seed)
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, 30)
    samples, status, last_tic, stall = [], "max_samples", -1, 0
    try:
        g.req("qSupported")
        # RAM writes must happen after C start-up (BSS/data init): stop once at the first rendered frame.
        fin = sym("I_FinishUpdate") & 0xFFFFFF
        assert g.req("Z0,%x,2" % fin) == "OK"; g.cont(); assert g.req("z0,%x,2" % fin) == "OK"
        if a.shadow is not None: assert g.req("M%x,1:%02x" % (sym("r92_shadow_on"), a.shadow)) == "OK"
        if a.mode is not None: assert g.req("M%x,2:%02x01" % (sym("r77_color_state"), a.mode)) == "OK"
        while len(samples) < a.max_samples:
            g.send("c")
            time.sleep(a.interval_ms / 1000 * (0.5 + rng.random()))
            g.proc.stdin.write(b"\x03"); g.proc.stdin.flush()
            try:
                r = g.recv(timeout=10)
            except TimeoutError:
                status = "interrupt_unsupported" if not samples else "timeout"; break
            except RuntimeError as e:
                status = "emulator_ended" if ("EOF" in str(e) or "exited" in str(e)) else "error: " + str(e); break
            if not (r.startswith("S") or r.startswith("T")):
                status = "unexpected " + r[:40]; break
            regs = g.req("g")
            pc = int(regs[17 * 8:18 * 8], 16) & 0xFFFFFF; sp = int(regs[15 * 8:16 * 8], 16) & 0xFFFFFF
            ret = int.from_bytes(g.readmem(sp, 4), "big") & 0xFFFFFF if 0xFF0000 <= sp < 0xFFFFFC else 0
            tic = int.from_bytes(g.readmem(tic_a, 4), "big")
            if tic < last_tic - 5: status = "demo_restarted"; break
            stall = stall + 1 if tic == last_tic else 0; last_tic = max(last_tic, tic)
            if tic > 0 and stall < 200: samples.append((tic, pc, ret))
            elif stall >= 2000: status = "demo_finished"; break
    finally:
        g.close()
    with open(out / "samples.tsv", "w") as f:
        for t, pc, ret in samples: f.write("%d\t%06x\t%06x\n" % (t, pc, ret))
    by = collections.Counter(find(text, addrs, pc) for _, pc, _ in samples)
    caller = collections.Counter((find(text, addrs, pc), find(text, addrs, ret)) for _, pc, ret in samples)
    n = max(len(samples), 1)
    top = [{"function": f, "samples": c, "share": round(c / n, 4)} for f, c in by.most_common(60)]
    pairs = [{"function": f, "caller_guess": cl, "samples": c, "share": round(c / n, 4)} for (f, cl), c in caller.most_common(60)]
    res = {"rom": a.rom, "shadow": a.shadow, "mode": a.mode, "samples": len(samples), "status": status,
           "tic_range": [samples[0][0], samples[-1][0]] if samples else None, "top": top, "top_with_caller_guess": pairs,
           "note": "wall-clock sampling of BlastEm; caller_guess is the long word at SP (exact only for leaf functions)"}
    (out / "PROFILE.json").write_text(json.dumps(res, indent=1) + "\n")
    lines = ["%6.2f%%  %6d  %s" % (100 * t["share"], t["samples"], t["function"]) for t in top]
    (out / "PROFILE.txt").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: res[k] for k in ("samples", "status", "tic_range")})); print("\n".join(lines[:30]))
    if not samples: sys.exit("no samples: " + status)


if __name__ == "__main__":
    main()
