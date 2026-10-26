#!/usr/bin/env python3
"""R71 PC sampler for an UNINSTRUMENTED ROM (BlastEm GDB RSP, no ROM change).

The ROM is not modified. After the first rendered frame the host enables the VDP horizontal interrupt by writing the
VDP control port through the RSP memory-write packet (register 0 bit 4, register 10 = LINES-1), puts a breakpoint on
the address stored in the HInt vector (0x70) and, at every hit, reads the interrupted PC from the 68000 exception
frame ([A7+2]). The emulated CPU is stopped while the host reads, so the emulated timeline is not perturbed except by
the (short) HInt service routine itself. Output: histogram of interrupted PCs.

Known biases (same as R68, which sampled with an in-ROM HInt handler): HInt fires only on active display lines, so
VBlank lines are not sampled; a PC is the NEXT instruction to run, i.e. heat belongs to the instruction just retired
(up to one instruction of skew; aggregate over basic blocks). This is a profile of WHERE the time goes, not a benchmark.
Usage: r71_pcsample.py --blastem B --rom R --elf E --out DIR [--lines 16] [--max-samples 400000] [--stop-tic 2134]
"""
import argparse, importlib.util, json, pathlib, random, sys, time


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def vdp_write(g, word):
    """16-bit write to the VDP control port (0xC00004) through the RSP memory-write packet."""
    r = g.req("M%x,2:%04x" % (0xC00004, word & 0xffff))
    if r != "OK":
        raise RuntimeError("VDP write %04x refused: %r" % (word, r))


def sample_loop(g, syms, lines=16, max_samples=400000, stop_tic=2134, max_seconds=1500, log=print):
    """g needs req/cont/readmem. Returns (hist, meta)."""
    t0 = time.monotonic()
    g.req("qSupported")
    ifu = syms["I_FinishUpdate"]
    assert g.req("Z0,%x,2" % ifu) == "OK"
    g.cont()                                   # first rendered frame: the game is running
    assert g.req("z0,%x,2" % ifu) == "OK"
    vec = int.from_bytes(g.readmem(0x70, 4), "big")
    log("HInt vector (0x70) -> %#x" % vec)
    reg0 = 0x04
    for name in ("regValues", "_regValues"):
        if name in syms:
            reg0 = g.readmem(syms[name], 1)[0]
            log("VDP shadow register 0 = %#04x (%s)" % (reg0, name)); break
    vdp_write(g, 0x8000 | (reg0 | 0x10))       # reg 0: horizontal interrupt enable
    vdp_write(g, 0x8A00 | ((lines - 1) & 0xff))  # reg 10: HInt every `lines` lines
    assert g.req("Z0,%x,2" % vec) == "OK"
    hist, meta = {}, {"vector": vec, "lines": lines, "samples": 0, "invalid_sp": 0, "status": "max_samples",
                      "tic_first": None, "tic_last": None, "regs_len": None}
    last_tic = 0
    started = False
    for n in range(max_samples):
        try:
            g.cont()
        except RuntimeError as e:
            if "exited" in str(e) or "EOF" in str(e):
                meta["status"] = "emulator_ended"; break
            raise
        except TimeoutError:
            meta["status"] = "no_hint_within_timeout"; break
        regs = g.req("g")
        meta["regs_len"] = len(regs)
        if len(regs) < 18 * 8:
            raise RuntimeError("unexpected 'g' reply length %d: %r" % (len(regs), regs[:60]))
        a7 = int(regs[15 * 8:16 * 8], 16)
        pc_here = int(regs[17 * 8:18 * 8], 16)
        if n < 3:
            log("sample %d: regs pc=%#x (vector %#x) a7=%#x" % (n, pc_here, vec, a7))
        if a7 & 1 or a7 < 0xE00000 or a7 > 0x1000000:
            meta["invalid_sp"] += 1
            continue
        pc = int.from_bytes(g.readmem(a7 + 2, 4), "big")
        if n % 256 == 0:
            tic = int.from_bytes(g.readmem(syms["_g_gametic"], 4), "big")
            if tic + 5 < last_tic:
                meta["status"] = "demo_restarted"; break
            if tic > last_tic: last_tic = tic
            if meta["tic_first"] is None and tic > 0: meta["tic_first"] = tic
            meta["tic_last"] = tic
            started = started or tic > 0
            if tic >= stop_tic:
                meta["status"] = "demo_end"; break
            if time.monotonic() - t0 > max_seconds:
                meta["status"] = "max_seconds"; break
        if not started:
            continue
        hist[pc] = hist.get(pc, 0) + 1
        meta["samples"] += 1
    meta["seconds"] = round(time.monotonic() - t0, 1)
    return hist, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True); ap.add_argument("--elf", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--label", default="rom")
    ap.add_argument("--lines", type=int, default=16); ap.add_argument("--max-samples", type=int, default=400000)
    ap.add_argument("--stop-tic", type=int, default=2134); ap.add_argument("--max-seconds", type=int, default=1500)
    ap.add_argument("--max-emulated-frames", type=int, default=150000); ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()
    mod = load_rsp()
    syms = mod.symbols(a.elf)
    for need in ("I_FinishUpdate", "_g_gametic"):
        assert need in syms, "missing symbol " + need
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    g = mod.RSP(a.blastem, a.rom, a.max_emulated_frames, a.timeout)
    try:
        hist, meta = sample_loop(g, syms, a.lines, a.max_samples, a.stop_tic, a.max_seconds)
    finally:
        g.close()
    meta["label"] = a.label
    (out / "samples.json").write_text(json.dumps({"meta": meta, "hist": {"%x" % k: v for k, v in sorted(hist.items())}}))
    print(json.dumps(meta))
    return 0 if meta["samples"] > 1000 else 3


if __name__ == "__main__":
    sys.exit(main())
