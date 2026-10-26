#!/usr/bin/env python3
"""R71 PC sampler for an UNINSTRUMENTED ROM (BlastEm GDB RSP, no ROM change).

The ROM file is not modified. After the first rendered frame the host enables the VDP horizontal interrupt (register 0\nbit 4, register 10 = LINES-1) by running a 22-byte snippet it writes to RAM (see inject_vdp_writes), puts breakpoints on\nthe addresses stored in the HInt (0x70) and VInt (0x78) vectors and, at every hit, reads the interrupted PC from the 68000\nexception frame ([A7+2]). The emulated CPU is stopped while the host reads, so the emulated timeline is not perturbed except by
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


def inject_vdp_writes(g, words, sp):
    """BlastEm's RSP has no register-write packet ('G' makes it exit) and a byte write to the VDP control port is
    duplicated into both halves of the word, so the VDP cannot be programmed directly. Instead: stopped at the entry of
    a function (I_FinishUpdate) the return address is at [A7]. A 68000 snippet (move.w #w,$C00004 ...; jmp original_return)
    is written to free stack space below A7 and the return address is replaced by the snippet address, so it runs right
    after the function returns (CCR is dead after a call; no register is touched). Returns the snippet address."""
    ret = int.from_bytes(g.readmem(sp, 4), "big")
    code = b""
    for w in words:
        code += bytes([0x33, 0xFC]) + (w & 0xffff).to_bytes(2, "big") + (0x00C00004).to_bytes(4, "big")   # move.w #w,$00C00004.l
    code += bytes([0x4E, 0xF9]) + ret.to_bytes(4, "big")                                                     # jmp ret.l
    snippet = (sp - 0x1800) & ~1
    r = g.req("M%x,%x:%s" % (snippet, len(code), code.hex()))
    if r != "OK":
        raise RuntimeError("snippet write refused: %r" % r)
    r = g.req("M%x,4:%08x" % (sp, snippet))
    if r != "OK":
        raise RuntimeError("return address write refused: %r" % r)
    return snippet, ret


def sample_loop(g, syms, lines=16, max_samples=400000, stop_tic=2134, max_seconds=1500, log=print):
    """g needs req/cont/readmem. Samples the interrupted PC at every horizontal interrupt (hist) and, as a fallback and
    cross-check, at every vertical interrupt (vhist, 60 Hz, phase-locked to the frame so biased). Returns (hist, vhist, meta)."""
    t0 = time.monotonic()
    g.req("qSupported")
    ifu = syms["I_FinishUpdate"]
    assert g.req("Z0,%x,2" % ifu) == "OK"
    g.cont()                                   # first rendered frame: the game is running
    assert g.req("z0,%x,2" % ifu) == "OK"
    hvec = int.from_bytes(g.readmem(0x70, 4), "big")
    vvec = int.from_bytes(g.readmem(0x78, 4), "big")
    log("HInt vector (0x70) -> %#x, VInt vector (0x78) -> %#x" % (hvec, vvec))
    reg0 = 0x04
    for name in ("regValues", "_regValues"):
        if name in syms:
            reg0 = g.readmem(syms[name], 1)[0]
            log("VDP shadow register 0 = %#04x (%s)" % (reg0, name)); break
    regs = g.req("g")
    sp = int(regs[15 * 8:16 * 8], 16)
    snippet, ret = inject_vdp_writes(g, [0x8000 | (reg0 | 0x10), 0x8A00 | ((lines - 1) & 0xff)], sp)
    log("VDP snippet at %#x, return to %#x (a7=%#x)" % (snippet, ret, sp))
    # the 68000 bus is 24 bit: break on the masked addresses, and on the raw ones too when they differ
    hv24, vv24 = hvec & 0xFFFFFF, vvec & 0xFFFFFF
    for a_ in sorted({hv24, vv24}):
        assert g.req("Z0,%x,2" % a_) == "OK"
    hvec, vvec = hv24, vv24
    hist, vhist = {}, {}
    meta = {"hint_vector": hvec, "vint_vector": vvec, "lines": lines, "hint_samples": 0, "vint_samples": 0, "invalid_sp": 0,
            "status": "max_samples", "tic_first": None, "tic_last": None, "regs_len": None, "stops": 0}
    last_tic, started = 0, False
    for n in range(max_samples):
        try:
            g.cont()
        except RuntimeError as e:
            if "exited" in str(e) or "EOF" in str(e):
                meta["status"] = "emulator_ended"; break
            raise
        except TimeoutError:
            meta["status"] = "timeout_no_stop"; break
        meta["stops"] += 1
        regs = g.req("g")
        meta["regs_len"] = len(regs)
        if len(regs) < 18 * 8:
            raise RuntimeError("unexpected 'g' reply length %d: %r" % (len(regs), regs[:60]))
        a7 = int(regs[15 * 8:16 * 8], 16)
        pc_here = int(regs[17 * 8:18 * 8], 16)
        if n < 4:
            log("stop %d: pc=%#x a7=%#x" % (n, pc_here, a7))
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
        if pc_here == hvec:
            hist[pc] = hist.get(pc, 0) + 1; meta["hint_samples"] += 1
        else:
            vhist[pc] = vhist.get(pc, 0) + 1; meta["vint_samples"] += 1
    meta["seconds"] = round(time.monotonic() - t0, 1)
    return hist, vhist, meta


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
        hist, vhist, meta = sample_loop(g, syms, a.lines, a.max_samples, a.stop_tic, a.max_seconds)
    finally:
        g.close()
    meta["label"] = a.label
    use_v = meta["hint_samples"] < 1000            # HInt did not work: the (biased) VInt histogram is all we have
    meta["profile_source"] = "vint" if use_v else "hint"
    (out / "samples.json").write_text(json.dumps({"meta": meta, "hist": {"%x" % k: v for k, v in sorted((vhist if use_v else hist).items())},
                                                  "vint_hist": {"%x" % k: v for k, v in sorted(vhist.items())}}))
    print(json.dumps(meta))
    return 0 if (meta["vint_samples"] if use_v else meta["hint_samples"]) > 1000 else 3


if __name__ == "__main__":
    sys.exit(main())
