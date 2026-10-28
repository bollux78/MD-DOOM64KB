#!/usr/bin/env python3
"""R82 stack high-water probe for an UNINSTRUMENTED ROM (BlastEm GDB RSP; one run, <=10000 frames).

SGDK keeps a stack-only reserve between the heap limit (*heapEnd) and the top of RAM.
At the first rendered frame this probe paints the unused part of that reserve (from *heapEnd
up to 128 bytes below the live SP) with 0xA5, lets the demo run, and before the frame cap
reads the reserve back: the lowest overwritten byte is the stack high-water mark of everything
that ran in between, interrupts included (VInt, music, DMA handlers).

With --bsp-symbol it also breaks on the recursive R_RenderBSPNode and records the highest
(root) and lowest SP seen there, i.e. the BSP depth reached (frame size from --bsp-frame).
Output: JSON on stdout and in --out.
"""
import argparse, importlib.util, json, pathlib, sys

PAT = 0xA5
RAM_TOP = 0xE1000000


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def sp_of(g):
    regs = g.req("g")
    return int(regs[15 * 8:16 * 8], 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True); ap.add_argument("--elf", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--label", default="")
    ap.add_argument("--max-emulated-frames", type=int, default=8000)
    ap.add_argument("--stop-tic", type=int, default=640, help="read back before the frame cap ends the emulator")
    ap.add_argument("--bsp-symbol", default="")
    ap.add_argument("--bsp-frame", type=int, default=48)
    a = ap.parse_args()
    assert 1 <= a.max_emulated_frames <= 10000
    rsp = load_rsp(); syms = rsp.symbols(a.elf)
    for k in ("I_FinishUpdate", "_g_gametic", "heapEnd", "_bend"):
        assert k in syms, k
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, 60)
    res = {"label": a.label, "rom": a.rom, "max_emulated_frames": a.max_emulated_frames}
    try:
        g.req("qSupported")
        ifu = syms["I_FinishUpdate"]
        assert g.req("Z0,%x,2" % ifu) == "OK"
        for _ in range(40):
            g.cont()
            if int.from_bytes(g.readmem(syms["_g_gametic"], 4), "big") >= 2:
                break
        heap_end = int.from_bytes(g.readmem(syms["heapEnd"], 4), "big") | 0xE0000000
        sp0 = sp_of(g) | 0xE0000000
        lo, hi = heap_end, sp0 - 128
        assert syms["_bend"] <= lo < hi < RAM_TOP, (hex(syms["_bend"]), hex(lo), hex(hi))
        for off in range(lo, hi, 256):
            n = min(256, hi - off)
            assert g.req("M%x,%x:%s" % (off & 0xFFFFFF, n, (bytes([PAT]) * n).hex())) == "OK"
        res.update(heap_end=hex(heap_end), bend=hex(syms["_bend"]), sp_at_paint=hex(sp0),
                   reserve_bytes=RAM_TOP - heap_end, painted_bytes=hi - lo, tic_painted=int.from_bytes(g.readmem(syms["_g_gametic"], 4), "big"))
        bsp = None
        if a.bsp_symbol:
            cand = [k for k in syms if k == a.bsp_symbol or k.startswith(a.bsp_symbol + ".")]
            assert len(cand) == 1, ("BSP symbol not unique", cand)
            bsp = syms[cand[0]]; res["bsp_symbol"] = cand[0]
            assert g.req("Z0,%x,2" % bsp) == "OK"
        bsp_max = bsp_min = None; bsp_hits = 0; tic = 0
        while True:
            g.cont()
            regs = g.req("g"); pc = int(regs[17 * 8:18 * 8], 16) & 0xFFFFFF; sp = int(regs[15 * 8:16 * 8], 16) | 0xE0000000
            if bsp and pc == (bsp & 0xFFFFFF):
                bsp_hits += 1
                bsp_max = sp if bsp_max is None else max(bsp_max, sp)
                bsp_min = sp if bsp_min is None else min(bsp_min, sp)
                continue
            tic = int.from_bytes(g.readmem(syms["_g_gametic"], 4), "big")
            if tic >= a.stop_tic:
                break
        mem = g.readmem(lo & 0xFFFFFF, hi - lo)
        first = next((i for i, b in enumerate(mem) if b != PAT), None)
        water = lo + first if first is not None else None
        res.update(tic_read=tic, gamemap=int.from_bytes(g.readmem(syms["_g_gamemap"], 2), "big") if "_g_gamemap" in syms else None,
                   high_water=hex(water) if water else None,
                   peak_stack_bytes=(RAM_TOP - water) if water else None,
                   headroom_bytes=(water - heap_end) if water else (hi - lo),
                   untouched=first is None)
        if bsp:
            res.update(bsp_hits=bsp_hits, bsp_root_sp=hex(bsp_max) if bsp_max else None, bsp_min_sp=hex(bsp_min) if bsp_min else None,
                       bsp_depth_reached=((bsp_max - bsp_min) // a.bsp_frame + 1) if bsp_hits else None, bsp_frame=a.bsp_frame)
        res["status"] = "ok"
    except Exception as e:  # keep partial results
        res["status"] = "error: %s" % e
    finally:
        g.close()
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))
    return 0 if res["status"] == "ok" else 3


if __name__ == "__main__":
    sys.exit(main())
