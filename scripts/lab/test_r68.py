#!/usr/bin/env python3
"""R68 host tests (no m68k toolchain, no BlastEm):
 1. C layout of r68_block_t (compiled with gcc) == the Python reader's struct, and the offsets
    hard-coded in r68_prof_hint.s == the C offsets;
 2. the reader's cost model recovers known cycles-per-unit from synthetic frames;
 3. end-to-end capture against a mock BlastEm that speaks the GDB RSP, checking every decoded
    field, the PC symbolization and the reports."""
import importlib.util, json, os, pathlib, re, stat, struct, subprocess, sys, tempfile, textwrap

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parents[1] / "src"
spec = importlib.util.spec_from_file_location("r68_capture", HERE / "r68_capture.py")
cap = importlib.util.module_from_spec(spec); spec.loader.exec_module(cap)


def test_layout(tmp):
    c = tmp / "lay.c"
    fields = ["ring", "head", "pad", "samples", "bad", "magic", "version", "ring_n", "frame",
              "vb_start", "vb_logic", "vb_end", "tic_start", "tic_end", "c"]
    body = "".join('printf("%s %%zu\\n", offsetof(r68_block_t, %s));' % (f, f) for f in fields)
    c.write_text('#include <stdio.h>\n#include <stddef.h>\n#include "r68_prof.h"\nint main(void){%s printf("size %%zu\\n", sizeof(r68_block_t)); return 0;}\n' % body)
    exe = tmp / "lay"
    subprocess.run(["gcc", "-DDOOM_R68_PROF", "-I", str(SRC), str(c), "-o", str(exe)], check=True)
    got = dict((k, int(v)) for k, v in (l.split() for l in subprocess.run([str(exe)], capture_output=True, text=True, check=True).stdout.splitlines()))
    assert got["size"] == cap.SIZE == 324, got
    # python-side offsets from the struct format
    off, expect = 0, {}
    expect["ring"] = 0; off = 2 * cap.RING
    for name, size in (("head", 2), ("pad", 2), ("samples", 4), ("bad", 4), ("magic", 4), ("version", 2), ("ring_n", 2),
                       ("frame", 4), ("vb_start", 4), ("vb_logic", 4), ("vb_end", 4), ("tic_start", 4), ("tic_end", 4)):
        expect[name] = off; off += size
    expect["c"] = off
    for k, v in expect.items():
        assert got[k] == v, (k, got[k], v)
    s = (SRC / "r68_prof_hint.s").read_text()
    ring = int(re.search(r"\.equ\s+R68_RING,\s*(\d+)", s).group(1))
    assert ring == cap.RING
    for sym, field in (("R68_OFF_HEAD", "head"), ("R68_OFF_SAMP", "samples"), ("R68_OFF_BAD", "bad")):
        expr = re.search(r"\.equ\s+%s,\s*([^\n]+)" % sym, s).group(1).strip().replace("R68_RING", str(ring))
        assert eval(expr) == got[field], (sym, expr, got[field])
    print("layout OK: C struct == Python reader == asm offsets (size %d)" % got["size"])


def make_frame(i):
    c = {k: 0 for k in cap.COUNTERS}
    c["seg"] = 30 + (i * 7) % 40; c["col"] = 150 + (i * 13) % 120; c["wall"] = 100 + (i * 5) % 60
    c["flat"] = 90 + (i * 3) % 50; c["bspnode"] = 80 + (i * 11) % 70; c["pta"] = 120 + (i % 9) * 5
    vb = 6 + (i % 5) * 2 + (4 if i % 17 == 0 else 0)
    ring = [0x1000 // 8 + (j * 37 + i) % 2000 for j in range(20 + i % 30)]
    return dict(frame=i, vb_start=1000 + i * 12, vb_logic=1000 + i * 12 + 2, vb_end=1000 + i * 12 + vb,
                tic_start=i, tic_end=i + 1, samples=len(ring) + (3 if i % 11 == 0 else 0), head=len(ring), bad=0, c=c, ring=ring)


def pack(f):
    ring = f["ring"] + [0] * (cap.RING - len(f["ring"]))
    return struct.pack(cap.FMT, *ring, f["head"], 0, f["samples"], f["bad"], cap.MAGIC, 1, cap.RING, f["frame"],
                       f["vb_start"], f["vb_logic"], f["vb_end"], f["tic_start"], f["tic_end"], *[f["c"][k] for k in cap.COUNTERS])


def test_fit():
    code = [(0x200, "main"), (0x1000, "alpha"), (0x2000, "beta"), (0x3000, "gamma")]
    truth = dict(seg=9000, col=700, wall=1500, flat=300, bspnode=400, pta=250); fixed = 120000
    frames = []
    for i in range(300):
        f = make_frame(i); cyc = fixed + sum(truth[k] * f["c"][k] for k in truth)
        vb = cyc / cap.VB_CYCLES
        f["vb_end"] = f["vb_start"] + vb; f["vb_logic"] = f["vb_start"] + vb * 0.1
        frames.append(f)
    with tempfile.TemporaryDirectory() as d:
        r = cap.analyze(frames, code, d)
    fit = r["fit"]; assert fit["r2"] > 0.999, fit["r2"]
    for k, v in truth.items():
        assert abs(fit["cycles_per_unit"][k] - v) / v < 0.02, (k, fit["cycles_per_unit"][k], v)
    print("cost model OK: R2=%.5f, coefficients within 2%% of the truth" % fit["r2"])


MOCK = r'''#!/usr/bin/env python3
import json, os, struct, sys
spec = json.load(open(os.environ["R68_MOCK"]))
frames = [bytes.fromhex(h) for h in spec["blocks"]]
PTR_SYM, PTR_VAL = spec["ptr_sym"], spec["ptr_val"]
gametic_sym = spec["gametic_sym"]
cur = [-1]
def mem(addr, n):
    out = bytearray(n)
    def put(a, data):
        for i, b in enumerate(data):
            p = a + i - addr
            if 0 <= p < n: out[p] = b
    put(PTR_SYM, struct.pack(">I", PTR_VAL))
    if cur[0] >= 0: put(PTR_VAL, frames[cur[0]])
    put(gametic_sym, struct.pack(">I", max(cur[0], 0) + 1))
    return bytes(out)
def reply(s):
    b = s.encode()
    sys.stdout.buffer.write(b"+$" + b + b"#" + b"%02x" % (sum(b) & 255)); sys.stdout.buffer.flush()
buf = bytearray(); fd = sys.stdin.buffer
while True:
    d = os.read(0, 4096)
    if not d: break
    buf.extend(d)
    while True:
        a = buf.find(b"$"); h = buf.find(b"#", a + 1) if a >= 0 else -1
        if a < 0 or h < 0 or len(buf) < h + 3: break
        cmd = bytes(buf[a + 1:h]).decode(); del buf[:h + 3]
        if cmd.startswith("qSupported"): reply("PacketSize=1000")
        elif cmd.startswith("Z0"): reply("OK")
        elif cmd == "c":
            cur[0] += 1
            if cur[0] >= len(frames): sys.exit(0)
            reply("S05")
        elif cmd.startswith("m"):
            addr, n = [int(x, 16) for x in cmd[1:].split(",")]
            reply(mem(addr, n).hex())
        else: reply("")
'''


def test_capture(tmp):
    n = 60
    frames = [make_frame(i) for i in range(n)]
    ptr_sym, ptr_val, gt_sym = 0xFF0020, 0xFF4000, 0xFF0030
    spec = dict(blocks=[pack(f).hex() for f in frames], ptr_sym=ptr_sym, ptr_val=ptr_val, gametic_sym=gt_sym)
    (tmp / "spec.json").write_text(json.dumps(spec))
    mock = tmp / "blastem"; mock.write_text(MOCK); mock.chmod(mock.stat().st_mode | stat.S_IEXEC)
    nm = tmp / "nm"
    nm.write_text("#!/bin/sh\ncat <<'EOF'\n00000200 T main\n00001000 T alpha\n00002000 T beta\n00003000 t gamma\n"
                  "00004000 T R68_FrameMark\n%08x B r68_ptr\n%08x B _g_gametic\nEOF\n" % (ptr_sym, gt_sym))
    nm.chmod(nm.stat().st_mode | stat.S_IEXEC)
    (tmp / "fake.elf").write_text("x"); (tmp / "fake.bin").write_text("x")
    os.environ["R68_MOCK"] = str(tmp / "spec.json"); os.environ["M68K_NM"] = str(nm)
    class A: pass
    a = A(); a.blastem = str(mock); a.rom = str(tmp / "fake.bin"); a.elf = str(tmp / "fake.elf")
    a.out = str(tmp / "out"); a.max_frames = 1000; a.max_emulated_frames = 10000; a.max_breaks = 1000
    a.start_tic = 1; a.timeout = 20.0
    r = cap.capture(a)
    assert r["frames"] == n - 0 or r["frames"] == n - 1, r["frames"]   # start_tic=1 drops frame 0 (tic_end=1 is kept: tic_end>=1)
    rows = [json.loads(l) for l in (tmp / "out/frames.jsonl").read_text().splitlines()]
    assert len(rows) == r["frames"]
    for row in rows:
        f = frames[row["frame"]]
        for k in ("vb_start", "vb_logic", "vb_end", "tic_start", "tic_end", "samples", "head"):
            assert row[k] == f[k], (row["frame"], k, row[k], f[k])
        assert row["c"] == f["c"]
    rings = json.loads((tmp / "out/rings.json").read_text())
    assert [len(x) for x in rings] == [len(frames[row["frame"]]["ring"]) for row in rows]
    assert rings[3] == frames[rows[3]["frame"]]["ring"]
    assert r["samples_lost"] == sum(max(0, f["samples"] - f["head"]) for f in frames if f["frame"] in {x["frame"] for x in rows})
    names = {x[0] for x in r["profile_all"]}
    assert {"alpha", "beta"} <= names, names
    assert abs(sum(x[2] for x in r["profile_all"]) - 1.0) < 0.35  # top-25 rows cover most of the 3 functions
    rep = (tmp / "out/report.md").read_text()
    assert "Share of total time in the slowest frames" in rep and "PC profile: Slowest 20%" in rep
    print("capture OK: %d frames decoded through a mock RSP, fields and PC buckets match, report written" % r["frames"])


def main():
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        (d / "a").mkdir(); (d / "b").mkdir()
        test_layout(d / "a"); test_fit(); test_capture(d / "b")
    print("PASS test_r68")


if __name__ == "__main__":
    main()
