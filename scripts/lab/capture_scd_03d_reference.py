#!/usr/bin/env python3
"""Capture eight reference framebuffers from the private, unmodified R128 PERF ROM."""
import argparse
import json
from hashlib import sha256
from pathlib import Path

from r64a_rsp_capture import RSP, symbols

TICS = {200, 210, 220, 230, 237, 245, 252, 260}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for option in ("blastem", "rom", "elf", "out"):
        p.add_argument("--" + option, required=True, type=Path)
    p.add_argument("--columns", action="store_true")
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
    kernels = {address: name for name in ("R60_WallColumn", "R113_WallColumn")
               if (address := sym(name, optional=True)) is not None}
    if a.columns:
        assert "R113_WallColumn" in kernels.values(), kernels
    trace = {tic: [] for tic in sorted(TICS)}
    sources, palettes = {}, {}

    def fb_address(g):
        return (int.from_bytes(g.readmem(draw_pointer, 4), "big") & 0xffffff
                if draw_pointer is not None else framebuffer)

    def collect(g, pc, regs, tic):
        reg = lambda i: int(regs[i*8:(i+1)*8], 16)
        phase, step, count, odd = (reg(i) & 0xffff for i in range(4))
        dst, src, lut, sp = (reg(i) & 0xffffff for i in (8, 9, 10, 15))
        offset = dst - fb_address(g)
        assert 1 <= count <= 44 and odd in (0, 1), (count, odd)
        touched = 1 + 152 * ((count + odd - 1) // 2)
        assert 0 <= offset and offset + touched <= 3344, (dst, offset, touched)
        tex = g.readmem(src, 128)
        low = g.readmem(lut, 256)
        shifted = (g.readmem(lut + 8704, 256) if kernels[pc] == "R113_WallColumn"
                   else bytes((value << 4) & 255 for value in low))
        assert all(value < 16 for value in low)
        before = g.readmem(dst, touched)[::152]
        ret = int.from_bytes(g.readmem(sp, 4), "big") & 0xffffff
        assert ret not in kernels and ret != finish
        bp(g, pc, False)
        bp(g, ret)
        g.cont()
        assert int(g.req("g")[17*8:18*8], 16) & 0xffffff == ret
        bp(g, ret, False)
        bp(g, pc)
        after = g.readmem(dst, touched)[::152]
        expected = bytearray(before)
        for row in range(count):
            y = row + odd
            color = tex[((phase + row * step) & 0xffff) >> 9]
            if y & 1:
                expected[y // 2] = (expected[y // 2] & 0xf0) | low[color]
            else:
                expected[y // 2] = (expected[y // 2] & 0x0f) | shifted[color]
        assert expected == after, (tic, kernels[pc], phase, step, count, odd,
                                   before.hex(), expected.hex(), after.hex())
        source = sha256(tex).hexdigest()
        palette = sha256(low + shifted).hexdigest()
        sources[source] = tex.hex()
        palettes[palette] = (low + shifted).hex()
        trace[tic].append(dict(kernel=kernels[pc], offset=offset, phase=phase, step=step,
                               count=count, odd=odd, source=source, palette=palette,
                               before=before.hex(), after=after.hex()))

    g = RSP(a.blastem, a.rom, 10000, 60)
    seen = set()
    try:
        g.req("qSupported")
        for point in (ticker, error, end):
            if point is not None:
                bp(g, point)
        armed = False
        columns_armed = False
        while seen != TICS:
            g.cont()
            regs = g.req("g")
            pc = int(regs[17*8:18*8], 16) & 0xffffff
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
            if pc in kernels and columns_armed:
                tic = read(g, "_g_gametic")
                if tic in TICS:
                    collect(g, pc, regs, tic)
                continue
            assert pc == finish, f"unexpected debugger stop at {pc:06x}"
            tic = read(g, "_g_gametic")
            assert tic <= max(TICS), f"missing reference frames: {sorted(TICS - seen)}"
            if a.columns:
                should_arm = tic + 1 in TICS
                if should_arm != columns_armed:
                    for point in kernels:
                        bp(g, point, should_arm)
                    columns_armed = should_arm
            if tic in TICS and tic not in seen:
                if a.columns:
                    assert trace[tic], f"no traced columns for {tic}"
                frame = g.readmem(fb_address(g), 3344)
                a.out.mkdir(parents=True, exist_ok=True)
                (a.out / f"r128-e1m1-tic-{tic}.bin").write_bytes(frame)
                print(f"R128 FRAME {tic} leveltime={read(g, '_g_leveltime')} {sha256(frame).hexdigest()}", flush=True)
                seen.add(tic)
    finally:
        g.close()
    if a.columns:
        (a.out / "column-trace.json").write_text(
            json.dumps(dict(frames=trace, textures=sources, palettes=palettes)) + "\n")
        print("R128 COLUMN PASS: exact destination bytes for",
              {tic: len(calls) for tic, calls in trace.items()})
    else:
        print("R128 REFERENCE PASS: eight framebuffer snapshots; no column trace")


if __name__ == "__main__":
    main()
