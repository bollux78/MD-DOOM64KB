#!/usr/bin/env python3
"""Collect verified C7 ROMs, geometry statistics and real measured FPS into one ZIP."""
import argparse,csv,json,zipfile,hashlib
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--roms",type=Path,required=True)
p.add_argument("--bench",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
args=p.parse_args()
names=("CONTROL",)
# Classes decide what a result means. "near_exact" must pass the host gate (verify_geo_exact.sh): same image apart from
# isolated edge pixels. Everything else is a trade-off that the project owner decides before it is called a speed-up.
CLASS={
    "CONTROL":"baseline",
    "GEO_SAFE":"near_exact",
    "AI6":"gameplay_change",              # monsters at 6 Hz, so also slower (every kind acts once per 10 VBlanks)
    "AI6S":"gameplay_change_speed_kept",  # 6 Hz, step lengthened to keep average speed; choppier, fastest kinds capped
    "ALL":"multi_change",                 # AI6S + GEO_SAFE
}
AI_CLASSES=("gameplay_change","gameplay_change_speed_kept","multi_change")
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
    gv=args.roms/f"geo-verify-{variant}.json"
    row["geo_gate_pass"]=json.loads(gv.read_text())["pass"] if gv.is_file() else ""
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
    # near_exact: the pass/fail gate is the host check (geo_gate_pass). This hash comparison is information only.
    if row["class"]=="near_exact":
        row["render_pixels_equal_control"]=(row["render_hash"]==control["render_hash"]) if row["render_hash"] and control["render_hash"] else ""
    else:
        row["render_pixels_equal_control"]="not_applicable"
    # AI variants change the combat workload: combat FPS is not a like-for-like comparison.
    row["combat_comparable"]=(row["class"] not in AI_CLASSES)
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
        for extra in (f"geo-verify-{variant}.txt",f"geo-verify-{variant}.json"):
            if (args.roms/extra).is_file():z.write(args.roms/extra,f"metadata/{extra}")
        for mode in (1,2):
            f=args.bench/f"{variant}-bench-{mode}.json"
            if f.exists():z.write(f,f"benchmarks/{f.name}")
    z.write(csvpath,"C7-PERFORMANCE.csv")
    z.write(jsonpath,"C7-PERFORMANCE.json")
    z.write(Path(__file__).with_name("README.md"),"README-EXPERIMENTOS.md")
with zipfile.ZipFile(args.out) as z:
    assert z.testzip() is None
    assert sum(x.filename.endswith(".bin") for x in z.infolist())==len(names)
print("CREATED",args.out,"bytes",args.out.stat().st_size)
for row in rows:print(json.dumps(row))
