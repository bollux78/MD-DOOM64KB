#!/usr/bin/env python3
"""Host tests of the R71 tools with synthetic data (NOT real ROM numbers): sampler loop against a fake RSP, asm report."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import r71_pcsample as S
import r71_asm_report as R

OBJ = """
00000100 <hot_fn>:
     100:\t4e56 0000      \tlink %fp,#0
     104:\t202e 0008      \tmovel %fp@(8),%d0
     108:\t5280           \taddql #1,%d0
     10a:\t6600 fffc      \tbnew 0x108 <hot_fn+0x8>
     10e:\t4e5e           \tunlk %fp
     110:\t4e75           \trts

00000112 <cold_fn>:
     112:\t4a39 00e0 0000 \ttstb 0xe00000
     118:\t4e75           \trts
"""


class FakeRSP:
    """HInt stops: the stacked PC cycles over a few addresses; gametic advances 1 per 100 samples."""
    def __init__(self):
        self.n = 0; self.mem = {}; self.log = []
    def req(self, c):
        self.log.append(c)
        if c == "qSupported": return "PacketSize=1000"
        if c.startswith(("Z0", "z0", "M", "G")): return "OK"
        if c == "g":
            return "".join("%08x" % v for v in [0] * 15 + [0xFFFF00, 0x2700, 0x300])
        raise AssertionError(c)
    def cont(self):
        self.n += 1; return "S05"
    def readmem(self, addr, n):
        if addr == 0x70: return (0x300).to_bytes(4, "big")
        if addr == 0x78: return (0x400).to_bytes(4, "big")
        if addr == 0xFFFF00 + 2: return [0x108, 0x10a, 0x108, 0x112][self.n % 4].to_bytes(4, "big")
        if addr == 0xFF0000: return (self.n // 100 + 1).to_bytes(4, "big")
        raise AssertionError(hex(addr))


def main():
    g = FakeRSP()
    hist, vhist, meta = S.sample_loop(g, {"I_FinishUpdate": 0x200, "_g_gametic": 0xFF0000}, lines=16, max_samples=5000, stop_tic=20, log=lambda *a: None)
    assert meta["status"] == "demo_end", meta
    assert meta["hint_samples"] > 1000 and sum(hist.values()) == meta["hint_samples"], meta
    snip = [c for c in g.log if c.startswith("M") and "33fc8014" in c.replace(" ", "")]
    assert snip and "33fc8a0f00c00004" in snip[0] and snip[0].endswith("4ef9" + "%08x" % 0x300), snip
    assert any(c.startswith("G") and c[1 + 17 * 8:1 + 18 * 8] != "00000300" for c in g.log), "PC redirected to the snippet"
    assert "Z0,300,2" in g.log and "Z0,400,2" in g.log, "breakpoints on both interrupt vectors"
    funcs, per_fn, heat, total, outside = R.build(OBJ, hist)
    assert per_fn["hot_fn"] + per_fn["cold_fn"] == total and not outside and per_fn["hot_fn"] > per_fn["cold_fn"]
    md, js = R.report("synthetic", funcs, per_fn, heat, total, outside)
    assert "Hottest basic blocks" in md and "hot_fn" in md and js["total"] == total
    bl = R.blocks_of(funcs["hot_fn"])
    assert [b[0]["addr"] for b in bl] == [0x100, 0x108, 0x10e], [hex(b[0]["addr"]) for b in bl]
    print("PASS test_r71_tools")


if __name__ == "__main__":
    main()
