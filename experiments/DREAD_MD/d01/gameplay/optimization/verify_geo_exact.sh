#!/usr/bin/env bash
# Host-side check of the geometry variants (no ROM, no emulator, no console).
# For each map and variant: convert with the C7 settings, build the PVS from the UNREDUCED seg tables, build the
# host renderer, render N views at the same positions (chosen inside the map by CONTROL), and compare framebuffers.
#
# Gate for the "near_exact" class (GEO_SAFE uses the "merge" mode): no blank frame, at most 2% of the views
# differ, and no view differs by more than 5% of its bytes. Edge pixels at the junction of a removed same-sector
# portal can move by one column, so bit-identical output is not promised; blank or broken frames are a bug.
# Also prints work counters (segs drawn, BSP nodes, column visits): they show whether a variant can be faster.
#
# Usage: verify_geo_exact.sh WAD "E1M1 E1M2" [VIEWS=3000] [OUTDIR] ["control merge"]
# Writes OUTDIR/summary.json. Exit 0 = gate passed, 3 = gate failed.
set -euo pipefail
wad=$(realpath "${1:?WAD}"); maps=${2:-E1M1}; views=${3:-3000}; out=$(realpath -m "${4:-/tmp/dread-geo-verify}")
variants=${5:-control merge}
here="$(cd "$(dirname "$0")" && pwd)"; root="$(cd "$here/../.." && pwd)"
export DREAD_COMBAT=1 DREAD_GAMEPLAY=1 DREAD_SKILL=easy DREAD_NPAL=1 OPENBLAS_NUM_THREADS=1
FL="-DDREAD_ROW_ONLY -DDREAD_COMBAT -DDREAD_GAMEPLAY -DDREAD_COMBAT_12_20"
mkdir -p "$out"
for m in $maps; do
  for v in $variants; do
    d="$out/$m-$v"; mkdir -p "$d"
    case $v in
      control|safe|merge) extra=(--render-geometry "$v") ;;
      steps) extra=(--render-geometry merge --simplify-steps) ;;
      *) echo "unknown variant $v" >&2; exit 2 ;;
    esac
    PYTHONPATH="$root/tools" python3 "$root/tools/conv.py" "$wad" "$m" "$d" --row-only --tex-pad 32 \
      --palette "$root/tools/gameplay_palette.json" "${extra[@]}" > "$d/conv.log" 2>&1
    pvsmap="$d/mapdata.c"; [[ -f "$d/mapdata_pvs.c" ]] && pvsmap="$d/mapdata_pvs.c"
    cc -O2 -DPVS_GEN -DDREAD_OPEN_PVS $FL -I"$d" -I"$root/src" -o "$d/pvsgen" "$root/tools/pvsgen.c" "$root/src/render.c" "$pvsmap" 2> "$d/cc1.log"
    "$d/pvsgen" "$d/pvs.c" > "$d/pvs.log" 2>&1
    cc -O2 $FL -I"$root/src" -I"$d" -o "$d/host" "$root/host/host.c" "$root/src/render.c" "$here/host_stubs.c" "$d/mapdata.c" "$d/pvs.c" 2> "$d/cc2.log"
    # control comes first and picks the positions; every later variant renders the same views
    "$d/host" "$d/x" cmp "$views" "$out/$m-views.txt" "$d/fb.bin" > "$d/cmp.txt"
  done
done
python3 - "$out" "$maps" "$variants" <<'PY'
import sys,json
import numpy as np
out,maps,variants=sys.argv[1],sys.argv[2].split(),sys.argv[3].split()
def num(t,k): return int([x for x in t.split() if x.startswith(k+"=")][0].split("=")[1])
res={"gate":"no blank frame, <=2% of views differ, max 5% of bytes","maps":{},"pass":True}
for m in maps:
    def load(v):
        tot=open(f"{out}/{m}-{v}/cmp.txt").read().strip().splitlines()[-1]
        fbb=num(tot,"fbbytes")
        fb=np.fromfile(f"{out}/{m}-{v}/fb.bin",dtype=np.uint8).reshape(-1,fbb)
        rep=json.load(open(f"{out}/{m}-{v}/geometry-report.json"))
        return fb,tot,rep
    ctl,ctot,_=load("control")
    res["maps"][m]={}
    print(f"== {m}: {len(ctl)} views")
    print(f"{'variant':8} {'segs':>6} {'views differ':>12} {'blank':>6} {'max diff %':>10}   work vs control: segs / nodes / column visits")
    for v in variants:
        fb,tot,rep=load(v)
        d=(fb!=ctl).sum(axis=1); pct=100*d/ctl.shape[1]
        blank=int(((fb==0xEE).all(axis=1) & ~(ctl==0xEE).all(axis=1)).sum())
        w=lambda k:round(100*(num(tot,k)/num(ctot,k)-1),2)
        row=dict(segs=rep["after"],views=len(ctl),views_differ=int((d>0).sum()),blank_views=blank,
                 max_diff_pct=round(float(pct.max()),2),segs_pct=w("segs"),nodes_pct=w("nodes"),colvisits_pct=w("colvisits"))
        ok=blank==0 and row["views_differ"]<=0.02*len(ctl) and row["max_diff_pct"]<=5
        row["pass"]=bool(ok) if v!="control" else True
        res["maps"][m][v]=row
        print(f"{v:8} {row['segs']:>6} {row['views_differ']:>12} {blank:>6} {row['max_diff_pct']:>10.2f}   {row['segs_pct']:+.2f}% / {row['nodes_pct']:+.2f}% / {row['colvisits_pct']:+.2f}%")
        if v in ("safe","merge") and not ok: res["pass"]=False
json.dump(res,open(f"{out}/summary.json","w"),indent=2)
print("GATE","PASS" if res["pass"] else "FAIL")
sys.exit(0 if res["pass"] else 3)
PY
