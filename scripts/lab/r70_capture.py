#!/usr/bin/env python3
"""R70 timedemo capture for ONE uninstrumented ROM (BlastEm GDB RSP, read-only, no ROM changes).

Sets a host breakpoint at I_FinishUpdate. At every hit it records the game tic, the vblank counter and the real
renderer framebuffer (r22_fb.pixels, 76x44 packed, 3344 B), hashed with SHA-256 and also stored raw so that
r70_compare.py can diff pixels, not just hashes. The former 10,000 emulated-frame cap was lifted by the maintainer for these
tests (2026-10-26): the capture now runs until the demo ends (tic restarts or stalls), the emulator exits, or the safety bounds hit.

Writes OUT/frames.bin (3344 B per frame, in order), OUT/frames.jsonl (i, tic, vb, sha256) and OUT/CAPTURE.json.
Partial results are kept if BlastEm ends or a read fails.
"""
import argparse, hashlib, importlib.util, json, pathlib, sys

PIXELS = 3344


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def capture_loop(g, syms, out, max_breaks, stall_breaks=300):
    """g needs req/cont/readmem. Returns (records, status). Stops when the tic restarts (new demo loop) or no new tic
    appears for stall_breaks consecutive hits (demo finished)."""
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    records, status = [], "max_breaks"
    g.req("qSupported")
    assert g.req("Z0,%x,2" % syms["I_FinishUpdate"]) == "OK"
    max_tic, stalled = 0, 0
    with open(out / "frames.bin", "wb") as fb_file, open(out / "frames.jsonl", "w") as jf:
        for i in range(max_breaks):
            try:
                g.cont()
            except RuntimeError as e:
                if "exited" in str(e) or "EOF" in str(e):
                    status = "emulator_ended"; break
                raise
            except TimeoutError:
                status = "timeout"; break
            tic = int.from_bytes(g.readmem(syms["_g_gametic"], 4), "big")
            vb = int.from_bytes(g.readmem(syms["_g_vblankCount"], 4), "big")
            if tic + 5 < max_tic:
                status = "demo_restarted"; break
            if tic > max_tic:
                max_tic, stalled = tic, 0
            else:
                stalled += 1
                if stalled >= stall_breaks:
                    status = "demo_finished"; break
            fb = g.readmem(syms["r22_fb"] + 4, PIXELS)
            fb_file.write(fb)
            rec = {"i": i, "tic": tic, "vb": vb, "sha256": hashlib.sha256(fb).hexdigest()}
            records.append(rec)
            jf.write(json.dumps(rec) + "\n")
            jf.flush()
    return records, status


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True)
    ap.add_argument("--elf", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--max-emulated-frames", type=int, default=150000)
    ap.add_argument("--max-breaks", type=int, default=60000)
    ap.add_argument("--timeout", type=float, default=120.0)
    a = ap.parse_args()
    if not 1 <= a.max_emulated_frames <= 1000000:
        ap.error("safety bound: 1..1000000 emulated frames per BlastEm invocation")
    rsp = load_rsp()
    syms = rsp.symbols(a.elf)
    missing = [k for k in ("I_FinishUpdate", "r22_fb", "_g_gametic", "_g_vblankCount") if k not in syms]
    if missing:
        raise SystemExit("ELF missing symbols: %s" % missing)
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, a.timeout)
    records, status = [], "error"
    try:
        records, status = capture_loop(g, syms, a.out, a.max_breaks)
    finally:
        g.close()
    res = {"label": a.label, "rom": a.rom, "elf": a.elf, "max_emulated_frames": a.max_emulated_frames,
           "frames": len(records), "status": status,
           "first_tic": records[0]["tic"] if records else None, "last_tic": records[-1]["tic"] if records else None,
           "last_vb": records[-1]["vb"] if records else None}
    (pathlib.Path(a.out) / "CAPTURE.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))
    if not records:
        sys.exit("no frames captured")


if __name__ == "__main__":
    main()
