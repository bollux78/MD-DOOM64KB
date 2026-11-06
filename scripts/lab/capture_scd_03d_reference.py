#!/usr/bin/env python3
"""Capture eight reference framebuffers from the private, unmodified R128 PERF ROM."""
import argparse
from hashlib import sha256
from pathlib import Path

from r64a_rsp_capture import RSP, symbols

TICS = {200, 210, 220, 230, 237, 245, 252, 260}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for option in ("blastem", "rom", "elf", "out"):
        p.add_argument("--" + option, required=True, type=Path)
    a = p.parse_args()
    syms = symbols(a.elf)

    def sym(base, optional=False):
        if base in syms:
            return syms[base] & 0xffffff
        values = [v & 0xffffff for k, v in syms.items() if k.startswith(base + ".")]
        if not values and optional:
            return None
        value, = values
        return value

    def read(g, key):
        return int.from_bytes(g.readmem(sym(key), 4), "big")

    def bp(g, address, enable=True):
        assert g.req(f"{'Z' if enable else 'z'}0,{address:x},2") == "OK"

    def byte(g, key, value):
        assert g.req(f"M{sym(key):x},1:{value:02x}") == "OK"

    ticker, finish, error = map(sym, ("G_Ticker", "I_FinishUpdate", "I_Error"))
    end = sym("R116_End", optional=True)
    draw_pointer = sym("r115_draw", optional=True)
    framebuffer = sym("r22_fb") + 4
    g = RSP(a.blastem, a.rom, 10000, 60)
    seen = set()
    try:
        g.req("qSupported")
        for point in (ticker, error, end):
            if point is not None:
                bp(g, point)
        armed = False
        while seen != TICS:
            g.cont()
            pc = int(g.req("g")[17*8:18*8], 16) & 0xffffff
            assert pc not in (error, end), f"game stopped at {pc:06x}; captured {sorted(seen)}"
            if pc == ticker:
                if not armed:
                    byte(g, "r116_sel", 1)
                    byte(g, "r116_norender", 1)
                    armed = True
                if read(g, "_g_gametic") >= 190:
                    byte(g, "r116_norender", 0)
                    bp(g, ticker, False)
                    bp(g, finish)
                continue
            assert pc == finish, f"unexpected debugger stop at {pc:06x}"
            tic = read(g, "_g_gametic")
            assert tic <= max(TICS), f"missing reference frames: {sorted(TICS - seen)}"
            if tic in TICS and tic not in seen:
                address = (int.from_bytes(g.readmem(draw_pointer, 4), "big") & 0xffffff
                           if draw_pointer is not None else framebuffer)
                frame = g.readmem(address, 3344)
                a.out.mkdir(parents=True, exist_ok=True)
                (a.out / f"r128-e1m1-tic-{tic}.bin").write_bytes(frame)
                print(f"R128 FRAME {tic} leveltime={read(g, '_g_leveltime')} {sha256(frame).hexdigest()}", flush=True)
                seen.add(tic)
    finally:
        g.close()
    print("R128 REFERENCE PASS: eight framebuffer snapshots; no column trace")


if __name__ == "__main__":
    main()
