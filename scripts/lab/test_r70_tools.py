#!/usr/bin/env python3
"""Host tests for the R70-A A/B tooling: objdump parser/statistics, capture loop (mock RSP), compare report."""
import hashlib, json, pathlib, random, subprocess, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r70_disasm_compare as dis
import r70_capture as cap

OBJDUMP = """
00025a00 <R_RenderSegLoop>:
   25a00:\t4e56 ffd8      \tlink %fp,#-40
   25a04:\t202e fffc      \tmovel %fp@(-4),%d0
   25a08:\t2039 e0ff defe \tmovel e0ffdefe <rw_scalestep>,%d0
   25a0e:\td0b9 e0ff def0 \taddl e0ffdef0 <rw_stopx>,%d0
   25a14:\t6700 0008      \tbeqw 25a1e <R_RenderSegLoop+0x1e>
   25a18:\t4eb9 0000 1234 \tjsr 1234 <R_DrawColumnFlat>
   25a1e:\t4cdf 3c04      \tmoveml %sp@+,%d2-%d5
   25a22:\t5342           \tsubqw #1,%d2
   25a24:\t51ca fff6      \tdbf %d2,25a1c <R_RenderSegLoop+0x1c>
   25a28:\t3030 2800      \tmovew %a0@(0,%d2:l),%d0
   25a2c:\t4e5e           \tunlk %fp
   25a2e:\t4e75           \trts

00025b00 <R_RenderSegLoop.lto_priv.0>:
   25b00:\t4e75           \trts
"""


def test_disasm():
    f = dis.parse(OBJDUMP)
    assert set(f) == {"R_RenderSegLoop", "R_RenderSegLoop.lto_priv.0"}
    s = dis.stats(f["R_RenderSegLoop"])
    assert s["insns"] == 12, s
    assert s["bytes"] == 4 + 4 + 6 + 6 + 4 + 6 + 4 + 2 + 4 + 4 + 2 + 2, s
    assert s["abs"] == 2 and s["stack"] == 2 and s["indirect"] == 1, s     # branch/jsr targets are not data accesses
    assert s["calls"] == 1 and s["branches"] == 3 and s["movem"] == 1, s     # beqw, jsr, dbf
    assert s["mem_total"] == 5, s
    assert set(dis.pick(f, "R_RenderSegLoop")) == {"R_RenderSegLoop", "R_RenderSegLoop.lto_priv.0"}
    assert dis.classify("#-40") == "imm" and dis.classify("%d2-%d5") == "reg" and dis.classify("%a0@(0,%d2:l)") == "indirect"
    assert dis.classify("%pc@(10)") == "pcrel" and dis.classify("e0ffdefe <x>") == "abs"
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        fake = d / "objdump"
        fake.write_text("#!/bin/sh\ncat %s\n" % (d / "text.txt"))
        fake.chmod(0o755)
        (d / "text.txt").write_text(OBJDUMP)
        better = OBJDUMP.replace("2039 e0ff defe \tmovel e0ffdefe <rw_scalestep>,%d0", "202e ffe0      \tmovel %fp@(-32),%d0")
        (d / "text2.txt").write_text(better)
        fake2 = d / "objdump2"
        fake2.write_text("#!/bin/sh\ncat %s\n" % (d / "text2.txt")); fake2.chmod(0o755)
        res = {}
        for lab, ex in (("ctl", fake), ("a1", fake2)):
            res[lab] = {"R_RenderSegLoop": {k: dis.stats(v) for k, v in dis.pick(dis.parse(subprocess.run([str(ex), "-d", "-z", "x"], capture_output=True, text=True).stdout), "R_RenderSegLoop").items()}}
        md = dis.report(res, ["ctl", "a1"], ["R_RenderSegLoop"])
        assert "abs -1" in md and "stack/fp +1" in md, md
        class Alt:                     # first call = control text, second = variant text
            pass
        shell = d / "objdump3"
        shell.write_text("#!/bin/sh\ncase \"$3\" in *ctl.elf) cat %s;; *) cat %s;; esac\n" % (d / "text.txt", d / "text2.txt")); shell.chmod(0o755)
        dis.run(str(shell), ["R_RenderSegLoop"], d / "o", [("ctl", "ctl.elf"), ("a1", "a1.elf")])
        md2 = (d / "o/DISASM-COMPARE.md").read_text()
        assert (d / "o/disasm-ctl-R_RenderSegLoop.txt").is_file()
        assert "Functions whose code differs" in md2 and "R_RenderSegLoop" in md2 and "-> " in md2, md2
        assert (d / "o/disasm-a1-changed-R_RenderSegLoop.txt").is_file()
    print("disasm parser/statistics OK")


class FakeRSP:
    """Plays a short timedemo: every cont() advances the tic and vblank counter and renders a deterministic framebuffer."""
    def __init__(self, syms, frames, end=True):
        self.syms, self.n, self.i, self.end = syms, frames, 0, end
    def req(self, c):
        return "OK"
    def cont(self):
        if self.i >= self.n:
            if self.end: raise RuntimeError("BlastEm RSP EOF")
        self.i += 1; return "S05"
    def readmem(self, addr, size):
        s = self.syms
        if addr == s["_g_gametic"]: return (self.i).to_bytes(4, "big")
        if addr == s["_g_vblankCount"]: return (100 + 9 * self.i).to_bytes(4, "big")
        if addr == s["r22_fb"] + 4: return make_fb(self.i)
        raise AssertionError(hex(addr))


def make_fb(tic):
    r = random.Random(tic); return bytes(r.randrange(256) for _ in range(cap.PIXELS))


def test_capture(tmp):
    syms = {"I_FinishUpdate": 0x1000, "r22_fb": 0xFF2000, "_g_gametic": 0xFF3000, "_g_vblankCount": 0xFF3004}
    recs, status = cap.capture_loop(FakeRSP(syms, 25), syms, tmp / "c", 1000)
    assert status == "emulator_ended" and len(recs) == 25, (status, len(recs))
    assert recs[0]["tic"] == 1 and recs[-1]["vb"] == 100 + 9 * 25
    raw = (tmp / "c/frames.bin").read_bytes()
    assert len(raw) == 25 * cap.PIXELS and hashlib.sha256(raw[:cap.PIXELS]).hexdigest() == recs[0]["sha256"]
    # demo finished: the tic stops advancing, the loop must stop by itself (no emulator end needed)
    class Stall(FakeRSP):
        def readmem(self, addr, size):
            if addr == self.syms["_g_gametic"]: return min(self.i, 10).to_bytes(4, "big")
            return super().readmem(addr, size) if addr != self.syms["r22_fb"] + 4 else make_fb(min(self.i, 10))
    recs, status = cap.capture_loop(Stall(syms, 10 ** 6, end=False), syms, tmp / "s", 100000, stall_breaks=50)
    assert status == "demo_finished" and recs[-1]["tic"] == 10 and len(recs) < 100, (status, len(recs))
    class Restart(FakeRSP):
        def readmem(self, addr, size):
            if addr == self.syms["_g_gametic"]: return ((self.i % 40) + 1).to_bytes(4, "big")
            return super().readmem(addr, size) if addr != self.syms["r22_fb"] + 4 else make_fb(self.i % 40)
    recs, status = cap.capture_loop(Restart(syms, 10 ** 6, end=False), syms, tmp / "r", 100000)
    assert status == "demo_restarted" and len(recs) == 39, (status, len(recs))
    print("capture loop OK (emulator end, demo stall and demo restart all stop with partial results kept)")


def synth(dirp, vb_per_tic, tics=90, pixel_diff_tics=()):
    dirp.mkdir(parents=True, exist_ok=True)
    vb, recs, blob = 1000, [], bytearray()
    for t in range(1, tics + 1):
        vb += vb_per_tic(t)
        fb = bytearray(make_fb(t))
        if t in pixel_diff_tics: fb[100] ^= 0x11; fb[3000] ^= 0x02
        blob += fb
        recs.append({"i": t - 1, "tic": t, "vb": vb, "sha256": hashlib.sha256(bytes(fb)).hexdigest()})
    (dirp / "frames.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    (dirp / "frames.bin").write_bytes(bytes(blob))


def test_compare(tmp):
    import r70_compare as cmp
    synth(tmp / "ctl", lambda t: 10 + (t % 4))
    synth(tmp / "a1", lambda t: 10 + (t % 4) - (1 if t % 5 == 0 else 0), tics=80)     # faster, fewer tics captured? (shorter capture)
    synth(tmp / "a2", lambda t: 10 + (t % 4), pixel_diff_tics=(7, 33))                # same speed, 2 frames differ
    synth(tmp / "a12", lambda t: 10 + (t % 4) + (1 if t > 60 else 0))                 # slower in the last third
    synth(tmp / "repeat", lambda t: 10 + (t % 4))
    rc = cmp.main(tmp / "out", ["ctl=%s" % (tmp / "ctl"), "a1=%s" % (tmp / "a1"), "a2=%s" % (tmp / "a2"), "a12=%s" % (tmp / "a12"), "repeat=%s" % (tmp / "repeat")])
    r = json.loads((tmp / "out/summary.json").read_text())
    v = r["variants"]
    assert rc == 2                                           # a2 has pixel differences
    assert r["common_tics"] == 79, r["common_tics"]          # 80 captured minus the first tic (no period)
    assert v["a1"]["delta_pct"] < 0 and v["a1"]["differing_frames"] == 0
    assert v["a2"]["differing_frames"] == 2 and v["a2"]["differing_bytes"] == 4, v["a2"]
    assert abs(v["a2"]["delta_pct"]) < 1e-9
    assert v["a12"]["delta_pct"] > 0 and v["a12"]["thirds_pct"][2] > 0.5 and v["a12"]["thirds_pct"][0] == 0
    assert v["repeat"]["differing_frames"] == 0 and v["repeat"]["same_vblank_sequence"] is True
    assert r["best_pixel_identical"] == "a1"
    md = (tmp / "out/REPORT.md").read_text()
    assert "PIXEL DIFFERENCES" in md and "a third of the demo got slower" in md and "tic 7" in md
    print("compare report OK (speedup, pixel diffs located, regression flag, repeat determinism)")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        test_disasm(); test_capture(d); test_compare(d)
    print("PASS test_r70_tools")
