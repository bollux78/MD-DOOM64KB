#!/usr/bin/env python3
"""Invariant oracle for gen_r52_ab.py output. Usage: test_r52_ab.py OUT_DIR [REPO]
Checks structure only: it does NOT prove visual quality."""
import json, re, struct, sys
from pathlib import Path

out = Path(sys.argv[1])
repo = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
hdr = (out / "r52_ab_tables.h").read_text()
rep = json.loads((out / "r52_ab_report.json").read_text())

def arr(name):
    m = re.search(re.escape(name) + r"\[\d+\]=\{(.*?)\};", hdr, re.S)
    assert m, name
    return [int(x) for x in re.findall(r"\d+", m.group(1))]

cb = int(re.search(r"R52_COLORMAP_BYTES (\d+)", hdr).group(1))
pal0, pal1 = arr("r52_pal0"), arr("r52_pal1")
even, odd = arr("r52_even"), arr("r52_odd")
ce, co = arr("r52_comp_even"), arr("r52_comp_odd")

assert len(pal0) == len(pal1) == 14 * 16
assert len(even) == len(odd) == 256
assert len(ce) == len(co) == cb and cb % 256 == 0 and 32 <= cb // 256 <= 64
# Index 0 is transparent black in every sub-palette of both planes.
assert all(pal0[i * 16] == 0 and pal1[i * 16] == 0 for i in range(14)), "slot 0 must be black"
# Valid Mega Drive CRAM words: only bits 1-3, 5-7, 9-11.
assert all(w & ~0x0EEE == 0 for w in pal0 + pal1), "invalid CRAM word"
policy = rep["args"].get("zero_policy", "allow")
lo = 1 if policy == "forbid" else 0
assert all(lo <= v <= 15 for v in even + odd), f"slot out of range / index 0 emitted under policy {policy}"
# Slots the optimiser did not use must not be mapped to.
used0 = len(rep["palette_slots"]["pal0"])
used1 = len(rep["palette_slots"]["pal1"])
assert max(even) <= used0 and max(odd) <= used1, "map uses an unfilled slot"

# Composed tables must equal parity map applied after COLORMAP.
wad = (repo / "scripts/doom64.wad").read_bytes()
count = struct.unpack_from(">h", wad, 4)[0]
dirofs = struct.unpack_from(">I", wad, 8)[0]
cm = None
for i in range(count):
    p = dirofs + 16 * i
    name = wad[p + 8:p + 16].split(b"\0", 1)[0].decode("ascii")
    if name == "COLORMAP":
        off = struct.unpack_from(">I", wad, p)[0]
        size = struct.unpack_from(">H", wad, p + 4)[0]
        cm = wad[off:off + size]
        break
assert cm is not None and len(cm) == cb, "COLORMAP mismatch with generated header"
assert all(ce[i] == even[cm[i]] and co[i] == odd[cm[i]] for i in range(cb)), "composed LUT mismatch"

# Tint consistency: report must be complete and finite for all 14 sub-palettes.
sub = rep["per_subpalette"]
assert len(sub) == 14 and all(0 <= s["blend_dE"] < 100 for s in sub)
# Luma constraint actually respected for most of the weight (sub-palette 0).
tau = rep["constraints"]["tau_luma"]
if tau < 1e8:
    assert sub[0]["pct_weight_luma_diff_gt32"] < 0.35, "too much weight above luma limit"

print("R52-AB oracle PASS:", out, "| warnings:", len(rep["warnings"]))
for w in rep["warnings"]:
    print("  warning:", w)
