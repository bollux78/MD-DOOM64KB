"""Replay round 4 and 5 captures using the corrected independent raster model.

Load and authenticate the seven original model modules first; apply only
the audited change to raster_state.py in the temporary model directory.
The ROM and raw memory remain local. Numeric summaries are exported.
"""
import importlib.util, pathlib, sys, json, tempfile, hashlib, argparse
P=pathlib.Path
def main():
    p=argparse.ArgumentParser()
    p.add_argument("root",type=P);p.add_argument("rom",type=P);p.add_argument("out",type=P)
    a=p.parse_args()
    rom=a.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest()=="47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267"
    path=P(__file__).parent.parent/"ferret-round5"/"compare.py"
    spec=importlib.util.spec_from_file_location("round5_compare",path)
    r5=importlib.util.module_from_spec(spec);spec.loader.exec_module(r5)
    all_results={};expected={4:4,5:18}
    with tempfile.TemporaryDirectory() as t:
        dest=P(t);r5.load_models(a.root,dest)
        target=dest/"raster_state.py"
        original=target.read_text()
        assert hashlib.sha256(target.read_bytes()).hexdigest()==r5.HASHES["raster_state.py"]
        changes=[
            ("if top>=bottom:continue","if top==0 and bottom==0:continue"),
            ("if floor:fill(floor_start,bottom,c1)","if floor:\n    # Kernels 11/17 explicitly clear D5 in lower+floor or floor-only branch.\n    floor_color=0 if variant in (11,17) and top>=rows[2] and bottom>=rows[3] else c1\n    fill(floor_start,bottom,floor_color)"),
            ("if cliptop[x]>=clipbottom[x] and not (variant in (10,11,16,17) and top<edge_top==edge_bottom<bottom):cliptop[x]=clipbottom[x]=0;depth[x]=inv","if (ceiling and bottom<edge_top) or (floor and top>=edge_bottom):cliptop[x]=clipbottom[x]=0;depth[x]=inv")
        ]
        for old,new in changes:
            assert original.count(old)==1
            original=original.replace(old,new)
        target.write_text(original)
        print("Corrected raster SHA256:",hashlib.sha256(target.read_bytes()).hexdigest(),flush=True)
        for round_no,run_id in [(4,45645383728),(5,45657627918)]:
            source=a.root/f"round{round_no}"/str(run_id)
            folders=sorted(x for x in source.glob("sram*-*") if (x/"summary.json").is_file())
            assert len(folders)==expected[round_no],(round_no,len(folders))
            results={}
            for folder in folders:
                v=r5.analyze(rom,folder);results[folder.name]=v
                bad=[]
                for row in v["rows"]:
                    for label in ("visibility","walls","sprites","chain"):
                        x=row[label]
                        if "error_type" in x or any(x.get(k,0) for k in ("framebuffer_diff","depth_diff","cliptop_diff","clipbottom_diff","tag_diff","transform_diff","callbacks")) or any(x.get(k,True) is False for k in ("records_equal","actors_equal","actor_list_equal","stream_match")):
                            bad.append({"scene":row["scene"],"stage":label,"detail":x})
                print(json.dumps({"round":round_no,"case":folder.name,"scenes":v["scenes"],"stage_pass":v["stage_pass"],"divergences":bad[:4]}),flush=True)
            all_results[str(round_no)]=results
    a.out.write_text(json.dumps(all_results,indent=2))
    totals={}
    for r,results in all_results.items():
        n=sum(v["scenes"] for v in results.values())
        totals[r]={"frames":n,"stage_pass":{k:sum(v["stage_pass"][k] for v in results.values()) for k in ("visibility","walls","sprites","chain")}}
    print("ROUND6 TOTALS "+json.dumps(totals),flush=True)
    if any(v["frames"]!=expected[int(r)]*16 or any(n!=v["frames"] for n in v["stage_pass"].values()) for r,v in totals.items()):sys.exit(2)
if __name__=="__main__":main()
