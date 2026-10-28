#!/usr/bin/env python3
"""Checks for apply_r82_d8088.py on the real R81 build scripts (no compilation)."""
import importlib.util, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("r82", ROOT / "scripts/lab/apply_r82_d8088.py")
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)

bs = (ROOT / "scripts/build_silent.fish").read_text()
lf = (ROOT / "scripts/lab/build_r35_linear.fish").read_text()

# as apply_r81.py leaves it: apply_r72_flat2d.py keeps only the text up to the first "exit $rc"
truncated = bs[:bs.index("exit $rc\n") + len("exit $rc\n")]
for src, n in ((bs, 2), (truncated, 1)):
    assert src.count(h.EXTRA_OLD) == n
    for key in ("IVO", "D88"):
        out = h.add_flags(src, h.FLAGS[key])
        assert out.count("$render_flags " + h.FLAGS[key] + '"') == n, key
        diff = [(a, b) for a, b in zip(src.split("\n"), out.split("\n")) if a != b]
        assert len(diff) == n and all("EXTRA_FLAGS" in a for a, _ in diff), diff

out = h.drop_bsp_iterative(lf)
assert "DOOM_R20_BSP_ITERATIVE" not in [l for l in out.split("\n") if l.startswith(h.PIXEL_PREFIX)][0]
changed = [(a, b) for a, b in zip(lf.split("\n"), out.split("\n")) if a != b]
assert len(changed) == 1 and changed[0][0].startswith(h.PIXEL_PREFIX), changed
# the 'control' (non-pixel) list keeps its own flag
assert "'-DDOOM_R20_BSP_ITERATIVE'" in [l for l in out.split("\n") if l.startswith("set -l control ")][0]
print("PASS R82 hook: IVO/D88 touch only the two EXTRA_FLAGS lines; BSPR only the pixel define list")

# naming: R81 builder text -> r82-<tag>-pf/pl (ROM file, header title and benchmark screen)
r81_builder = ("    ('r81-'+label+'-'+suffix,mode,{})\n    for label,strength in (('menu',0),)\n")
named = h.rename(r81_builder, "p1f1")
assert "('r82-'+label+'-'+suffix" in named and "(('p1f1',0),)" in named and "r81-" not in named
for bad in ("P1F1", "p1f1+bspr", "x" * 40):
    try:
        h.rename(r81_builder, bad); raise SystemExit("bad tag accepted: " + bad)
    except AssertionError:
        pass
print("PASS R82 naming: r82-<tag>-pf/pl, invalid tags refused")
