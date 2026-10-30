#!/usr/bin/env python3
"""R93b: DEMO3 capture of an R92 toggle PERF ROM with Shadow On and a chosen colour mode.

Read-only except for two RAM bytes written once at the first stop (no ROM change):
  r92_shadow_on = 1, r77_color_state.mode = 1 (A2) or 2 (L3), r77_color_state.dirty = 1.
Two breakpoints per rendered frame:
  I_FinishUpdate entry -> framebuffer low bytes are this frame's pre-pass codes (the keys);
  R92_AfterPass        -> framebuffer after the shadow pass (attribute bit 15 of A = normal state).
Writes OUT/pre.bin, OUT/post.bin (3344 B per frame), OUT/frames.jsonl, OUT/CAPTURE.json.
BlastEm automation stays within --max-emulated-frames (<= 10000, AGENTS.md).
"""
import argparse, importlib.util, json, pathlib, sys

PIXELS = 3344


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def sym(syms, name):
    if name in syms: return syms[name]
    m = [v for k, v in syms.items() if k.startswith(name + ".")]
    assert len(m) == 1, (name, m)
    return m[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True)
    ap.add_argument("--elf", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--mode", type=int, choices=(1, 2), required=True, help="1=A2, 2=L3")
    ap.add_argument("--max-emulated-frames", type=int, default=8000)
    ap.add_argument("--max-breaks", type=int, default=12000)
    ap.add_argument("--timeout", type=float, default=600.0)
    a = ap.parse_args()
    assert 1 <= a.max_emulated_frames <= 10000
    rsp = load_rsp(); syms = rsp.symbols(a.elf)
    fb = sym(syms, "r22_fb") + 4; tic_a = sym(syms, "_g_gametic"); vb_a = sym(syms, "_g_vblankCount")
    on_a = sym(syms, "r92_shadow_on"); col_a = sym(syms, "r77_color_state")
    try: rect_a = sym(syms, "r92_rect")
    except AssertionError: rect_a = None
    fin = sym(syms, "I_FinishUpdate") & 0xFFFFFF; after = sym(syms, "R92_AfterPass") & 0xFFFFFF
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=False)
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, a.timeout)
    status, n, armed, pre, max_tic, stalled = "max_breaks", 0, False, None, 0, 0
    try:
        g.req("qSupported")
        assert g.req("Z0,%x,2" % fin) == "OK" and g.req("Z0,%x,2" % after) == "OK"
        with open(out / "pre.bin", "wb") as fpre, open(out / "post.bin", "wb") as fpost, open(out / "frames.jsonl", "w") as jf:
            for _ in range(a.max_breaks):
                try:
                    g.cont()
                except RuntimeError as e:
                    if "exited" in str(e) or "EOF" in str(e): status = "emulator_ended"; break
                    raise
                except TimeoutError:
                    status = "timeout"; break
                pc = int(g.req("g")[17 * 8:18 * 8], 16) & 0xFFFFFF
                if not armed:
                    assert g.req("M%x,1:01" % on_a) == "OK"
                    assert g.req("M%x,2:%02x01" % (col_a, a.mode)) == "OK"   # mode, dirty
                    armed = True
                    continue
                if pc == fin:
                    pre = g.readmem(fb, PIXELS); continue
                if pc != after or pre is None: continue
                post = g.readmem(fb, PIXELS)
                tic = int.from_bytes(g.readmem(tic_a, 4), "big"); vb = int.from_bytes(g.readmem(vb_a, 4), "big")
                st = g.readmem(col_a, 3); on = g.readmem(on_a, 1)[0]; rect = list(g.readmem(rect_a, 4)) if rect_a else None
                if tic + 5 < max_tic: status = "demo_restarted"; break
                if tic > max_tic: max_tic, stalled = tic, 0
                else:
                    stalled += 1
                    if stalled >= 300: status = "demo_finished"; break
                fpre.write(pre); fpost.write(post); pre = None
                jf.write(json.dumps({"i": n, "tic": tic, "vb": vb, "mode": st[0], "palette": st[2], "shadow_on": on, "rect": rect}) + "\n")
                n += 1
    finally:
        g.close()
    res = {"rom": a.rom, "mode": a.mode, "frames": n, "status": status, "last_tic": max_tic}
    (out / "CAPTURE.json").write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res))
    if n == 0: sys.exit("no frames captured")


if __name__ == "__main__":
    main()
