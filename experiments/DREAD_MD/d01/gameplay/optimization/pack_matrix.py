#!/usr/bin/env python3
"""Collect verified C7 ROMs, geometry statistics and real measured FPS into one ZIP."""
import argparse,csv,json,zipfile,hashlib
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--roms",type=Path,required=True)
p.add_argument("--bench",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
args=p.parse_args()
names=("CONTROL","AI6","AI4","TEX2","TEX4","GEO_SAFE","GEO_STEPS","ALL")
# Classes decide what a result means. Only "exact" variants are optimisations in the
# strict sense: same gameplay, same collisions, same pixels. Everything else is a trade-off
# that must be decided by the project owner before it is reported as a speed-up.
CLASS={
    "CONTROL":"baseline",
    "GEO_SAFE":"exact",          # expected identical pixels and gameplay: gate below
    "AI6":"gameplay_change",     # monsters act at 6 Hz
    "AI4":"gameplay_change",     # monsters act at 4 Hz
    "TEX2":"visual_change",      # walls sampled at 4x2 texels
    "TEX4":"visual_change",      # walls sampled at 8x4 texels
    "GEO_STEPS":"collision_change",  # floors and collisions simplified
    "ALL":"multi_change",        # AI6 + TEX2 + GEO_SAFE: includes trade-offs
}
rows=[]
for variant in names:
    rom=args.roms/f"DREAD-C7-OPT-{variant}.bin"
    assert rom.exists() and 0<rom.stat().st_size<=4194304,(variant,"missing/oversize")
    geom=args.roms/"geometry"/variant
    assert len(list(geom.glob("E1M*.json")))==9,(variant,"geometry reports missing")
    row={"variant":variant,"bytes":rom.stat().st_size,
         "sha256":hashlib.sha256(rom.read_bytes()).hexdigest(),
         "segs_e1m1":json.loads((geom/"E1M1.json").read_text())["after"],
         "segs_e1m8":json.loads((geom/"E1M8.json").read_text())["after"]}
    row["class"]=CLASS[variant]
    for mode,key in ((1,"render"),(2,"combat")):
        f=args.bench/f"{variant}-bench-{mode}.json"
        row[key+"_fps"]=row[key+"_frames"]=row[key+"_vblanks"]=""
        row[key+"_vpf"]=row[key+"_hash"]=""
        if f.is_file():
            d=json.loads(f.read_text())
            assert int(d["mode"])==mode
            row[key+"_fps"]=float(d["fps"])
            row[key+"_frames"]=int(d["frames"])
            row[key+"_vblanks"]=int(d["vblanks"])
            row[key+"_vpf"]=d.get("vblanks_per_frame_mean","")
            row[key+"_hash"]=d.get("visual_hash","")
    rows.append(row)
control=rows[0]
for row in rows:
    for key in ("render","combat"):
        cfps=control[key+"_fps"]
        value=row[key+"_fps"]
        row[key+"_delta_pct"]=round(100*(value/cfps-1),2) if cfps and value else ""
    # Gate for "exact" variants: same final image as CONTROL on the render route.
    # Mismatch is reported, not hidden; the release is still built so the owner can see it.
    if row["class"]=="exact":
        row["render_pixels_equal_control"]=(row["render_hash"]==control["render_hash"]) if row["render_hash"] and control["render_hash"] else ""
    else:
        row["render_pixels_equal_control"]="not_applicable"
    # AI variants change the combat workload: combat FPS is not a like-for-like comparison.
    row["combat_comparable"]=(row["class"] not in ("gameplay_change","multi_change"))
args.out.parent.mkdir(parents=True,exist_ok=True)
csvpath=args.out.with_suffix(".csv")
jsonpath=args.out.with_suffix(".json")
with csvpath.open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
jsonpath.write_text(json.dumps(rows,indent=2)+"\n")
with zipfile.ZipFile(args.out,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for variant in names:
        z.write(args.roms/f"DREAD-C7-OPT-{variant}.bin",f"DREAD-C7-OPT-{variant}.bin")
        z.write(args.roms/f"SHA256-{variant}.txt",f"SHA256-{variant}.txt")
        z.write(args.roms/f"manifest-{variant}.json",f"metadata/{variant}.json")
        for f in sorted((args.roms/"geometry"/variant).glob("E1M*.json")):
            z.write(f,f"geometry/{variant}/{f.name}")
        for mode in (1,2):
            f=args.bench/f"{variant}-bench-{mode}.json"
            if f.exists():z.write(f,f"benchmarks/{f.name}")
    z.write(csvpath,"C7-PERFORMANCE.csv")
    z.write(jsonpath,"C7-PERFORMANCE.json")
    z.write(Path(__file__).with_name("README.md"),"README-EXPERIMENTOS.md")
with zipfile.ZipFile(args.out) as z:
    assert z.testzip() is None
    assert sum(x.filename.endswith(".bin") for x in z.infolist())==8
print("CREATED",args.out,"bytes",args.out.stat().st_size)
for row in rows:print(json.dumps(row))
