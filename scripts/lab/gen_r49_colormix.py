#!/usr/bin/env python3
"""Generate R49 ROM-only composite colormap and conservative Pair-V ColorMix.

The original R22 palette is preserved verbatim as PAL0. PAL1 adds 15 colors
selected from Doom's PLAYPAL by greedy error reduction. A 4x4 sample is eligible
for a PAL1 mixture only when its *computed* average-color error is lower than
the original PAL0 solid, for every one of the 14 original subpalettes.

No improvement is assumed from two-plane alpha blending: VDP merely selects
opaque spatial pixels. This is a palette-space quality gate, not an assertion
of human preference; large stripe contrasts are penalized.
"""
from __future__ import annotations
from pathlib import Path
import re, runpy, struct, json

R = Path(__file__).resolve().parents[2]
g = runpy.run_path(str(R / "scripts/genpal.py"))
p = (R / "src/r22_palette.h").read_text()
m = re.search(r"r22_color\[256\]=\{([^}]+)\}", p)
assert m, "Run gen_r22_pixel4.py first"
BASE = [int(i) for i in m.group(1).split(",")]
assert len(BASE)==256
m = re.search(r"r22_cram\[14\]\[16\]=\{(.*)\};", p, re.S)
assert m
rows = re.findall(r"\{([^}]+)\}", m.group(1))
CRAM0 = [[int(i) for i in r.split(",")] for r in rows]
assert len(CRAM0)==14 and all(len(row)==16 for row in CRAM0)

raw = g["load_playpal"]()
SRC = [g["decode_subpal"](raw, i) for i in range(14)]
rgb = g["gen_to_rgb"]
color = g["gen_color"]
D = lambda a,b: sum((a[k]-b[k])**2 for k in range(3))
BASE_RGB = [[rgb(c) for c in row] for row in CRAM0]

# PAL1 index0 = transparent black; choose 15 *additional* colors among original
# indices, optimizing distortion relative to the untouched 16-color baseline.
pick=[]
base_err=[D(SRC[0][ci], BASE_RGB[0][BASE[ci]]) for ci in range(256)]
best=base_err[:]
candidate_words=[color(SRC[0][i]) for i in range(256)]
for _ in range(15):
    winner=None
    value=-1
    for ci,w in enumerate(candidate_words):
        if w==0 or w in [candidate_words[j] for j in pick]:
            continue
        v=rgb(w)
        gain=sum(max(0,best[k]-D(SRC[0][k],v)) for k in range(256))
        if gain>value:
            value,winner=gain,ci
    assert winner is not None
    pick.append(winner)
    v=rgb(candidate_words[winner])
    best=[min(best[k],D(SRC[0][k],v)) for k in range(256)]

P1=[[0]+[color(sub[i]) for i in pick] for sub in SRC]
P1_RGB=[[rgb(c) for c in row] for row in P1]

# For each solid baseline index choose one PAL1 color pair per ratio; the
# two vertical fragments are physically 4px wide (2:2, 3:1, or 1:3).
# No per-pixel RGB evaluation is performed on the Mega Drive.
ratios={"50":(2,2),"75a":(3,1),"75b":(1,3)}
pairs={}
gates={}
metrics={}
for ratio,(wa,wb) in ratios.items():
    PA=[0]*16; PB=[0]*16
    gate=[0]*256
    for base in range(16):
        members=[ci for ci in range(256) if BASE[ci]==base]
        if not members:
            continue
        top_score=-1
        top_pair=(0,0)
        for a in range(16):
            for b in range(16):
                # Large high-frequency vertical contrast is undesirable.
                ca,cb=P1_RGB[0][a],P1_RGB[0][b]
                sep=D(ca,cb)
                if max(abs(ca[k]-cb[k]) for k in range(3))>48:
                    continue
                predicted=tuple((wa*ca[k]+wb*cb[k])/4 for k in range(3))
                stripe_cost=sep*0.06*wa*wb/4
                val=sum(max(0.0,base_err[ci]-D(SRC[0][ci],predicted)
                            -stripe_cost-0.08*base_err[ci]-64) for ci in members)
                if val>top_score:
                    top_score,top_pair=val,(a,b)
        PA[base],PB[base]=top_pair
        for ci in members:
            old=[D(SRC[sp][ci],BASE_RGB[sp][base]) for sp in range(14)]
            newer=[]
            for sp in range(14):
                ca,cb=P1_RGB[sp][PA[base]],P1_RGB[sp][PB[base]]
                q=tuple((wa*ca[k]+wb*cb[k])/4 for k in range(3))
                contrast=D(ca,cb)*0.06*wa*wb/4
                newer.append(D(SRC[sp][ci],q)+contrast)
            # Strict all-subpalettes gate. Allow solid PAL1 refinements where
            # the mixed partners happen to coincide.
            if all(newer[s]+64 < old[s]*0.92 for s in range(14)):
                gate[ci]=1
    pairs[ratio]=(PA,PB)
    gates[ratio]=gate
    metrics[ratio]={"eligible_source_indices":sum(gate),
                    "chosen_pairs":sorted(set((PA[c],PB[c]) for c in BASE))}
    # Check invariant of gate, including its exact stripe penalty.
    for ci,enabled in enumerate(gate):
        if not enabled: continue
        base=BASE[ci]
        for sp in range(14):
            ca,cb=P1_RGB[sp][PA[base]],P1_RGB[sp][PB[base]]
            q=tuple((wa*ca[k]+wb*cb[k])/4 for k in range(3))
            newerr=D(SRC[sp][ci],q)+D(ca,cb)*0.06*wa*wb/4
            olderr=D(SRC[sp][ci],BASE_RGB[sp][base])
            assert newerr+64<olderr*0.92,(ratio,ci,sp)

# Extract original Doom colormap: convert WAD endianness is irrelevant to lump
# contents. An offset inside COLORMAP refers to one 256-byte LUT.
wad = (R/"scripts/doom64.wad").read_bytes()
assert wad[:4] == b"IWAD"
count,offset=struct.unpack_from(">hI",wad,4)
lumps={}
for i in range(count):
    a=offset+16*i
    pos,sz=struct.unpack_from(">IH",wad,a)
    name=wad[a+8:a+16].split(b"\0")[0].decode("ascii")
    lumps[name]=wad[pos:pos+sz]
colormap=lumps["COLORMAP"]
assert len(colormap)%256==0
LEVELS=len(colormap)//256
assert 32<=LEVELS<=64,LEVELS
comp=[BASE[ci] for ci in colormap]

def arr(name, values, typ="uint8_t", width=32):
    xs=[str(i) for i in values]
    lines=[",".join(xs[i:i+width]) for i in range(0,len(xs),width)]
    return "static const "+typ+" "+name+"["+str(len(xs))+"]={\n"+",\n".join(lines)+"\n};\n"

h=["/* Generated R49 ColorMix tables. Never edit by hand. */",
   "#ifndef DOOM_R49_COLORMIX_TABLES_H",
   "#define DOOM_R49_COLORMIX_TABLES_H",
   "#define R49_COLORMAP_BYTES "+str(len(colormap)),
   arr("r49_palette1", [w for row in P1 for w in row], "uint16_t",16)]
for suffix in ratios:
    pa,pb=pairs[suffix]
    h.append(arr("r49_mix_a_"+suffix,pa))
    h.append(arr("r49_mix_b_"+suffix,pb))
    h.append(arr("r49_mix_ok_"+suffix,gates[suffix]))
h.append(arr("r49_compmap",comp))
for suffix in ratios:
    h.append(arr("r49_compgate_"+suffix, [gates[suffix][ci] for ci in colormap]))
h.append("#endif")
(R/"src/r49_colormix_tables.h").write_text("\n".join(h)+"\n")
(R/"src/r49_colormix_report.json").write_text(json.dumps({
    "ratio_metrics":metrics,"pal1_original_color_indices":pick,
    "baseline_original_colors":16,"new_colors_pal1":15,
    "colormap_levels":LEVELS,"quality_gate":"all 14 subpalettes; avg RGB squared-error >=8% lower and >64 error margin, stripe penalty",
},indent=2)+"\n")
print("R49 ROM ColorMix generated: 14x16 PAL1, 3 ratio gates,",
      LEVELS,"colormaps, metrics:",metrics)
