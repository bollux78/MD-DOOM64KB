"""Differential tests of compiled visibility, without original Ferret ROM.
All original WAD data and compiled programs remain in the user's private folder.
"""
import argparse, collections, functools, json, pathlib, time, math
from compiler import WAD, Resources, geometry, bsp_order, name, need
from visibility_compile import Compiler, find_leaf, ordered_leaves, occludes, pack
from render_scene import view, sample_table, load_native, make_fixture
P=pathlib.Path
def cell_sector(g,leaf):
    n,a=g["subsectors"][leaf]
    need(n>0,"empty leaf")
    _,_,_,lid,d,_=g["segs"][a]
    side=g["lines"][lid][5+d]
    return g["sectors"][g["sides"][side][-1]]
def tests():
    cs=((-2,-2),(-2,2),(2,-2),(2,2))
    # Directed wall faces left; one target fully covered and one peeking out.
    cs=((-42,-2),(-42,2),(-38,-2),(-38,2))
    assert occludes((0,64),(0,-64),(40,-8),(40,8),cs)
    assert not occludes((0,64),(0,-64),(40,150),(40,160),cs)
    assert not occludes((0,64),(0,-64),(-20,-8),(-20,8),cs)
    assert not occludes((0,-64),(0,64),(40,-8),(40,8),cs)
def cameras(g,c,zigzag):
    out=[]
    def add(label,x,y,angles):
        leaf=find_leaf(g,x,y);s=cell_sector(g,leaf);box=c.cells[leaf][0]
        if box is None or not(box[0]<=x<=box[2] and box[1]<=y<=box[3]) or s[1]-s[0]<42:return
        for a in angles:
            pose=(x,y,s[0]+41,a%360)
            if not any(v[1]==pose for v in out):
                out.append((label,pose,leaf,name(s[2])))
    x,y,angle=next(t for t in g["things"] if t[3]==1)[:3]
    add("spawn",x,y,(angle+i*45 for i in range(8)))
    if zigzag:
        # Reference coordinates from earlier Alpha2 captures, on Doom geometry.
        # Height comes from this WAD's local sector, not the Ferret ROM.
        add("zigzag-reference",2980,170,range(0,360,45))
        for dx,dy in ((-32,0),(32,0),(0,-32),(0,32),(-64,0),(64,0)):
            add("zigzag-nearby",2980+dx,170+dy,range(0,360,90))
        # Include actual neighboring acid cells. Some may be in the pond, not on the walkway.
        candidates=[]
        for i,(box,p,_) in c.cells.items():
            if p is None or find_leaf(g,*p)!=i:continue
            s=cell_sector(g,i);dist=(p[0]-2980)**2+(p[1]-170)**2
            if name(s[2]).startswith("NUKAGE") and dist<768**2:candidates.append((dist,p))
        for _,p in sorted(candidates)[:4]:add("acid-cell",*p,range(0,360,90))
    # Distributed deterministic interior points, not only the spawn and target room.
    valid=[p for i,(_,p,_) in c.cells.items() if p is not None and find_leaf(g,*p)==i]
    stride=max(1,len(valid)//12)
    for p in valid[::stride][:12]:add("distributed",*p,(0,90,180,270))
    return out
def analyze(lib,wad,k,out,zigzag=False):
    g=geometry(wad,k);r=Resources(wad);c=Compiler(g)
    r.color=functools.lru_cache(maxsize=256)(r.color)
    r.packed_texture=functools.lru_cache(maxsize=128)(r.packed_texture)
    out.mkdir(parents=True,exist_ok=True)
    results={}
    for mode in ("backface","occlusion"):
        t=time.monotonic();compiled=c.compile(mode);elapsed=time.monotonic()-t
        blob,packing=pack(g,compiled);(out/f"{mode}.frv").write_bytes(blob)
        results[mode]={"compiled":compiled,"summary":{"bytes":len(blob),"compile_seconds":round(elapsed,3),"cells":len(compiled),"total_segments":len(g["segs"]),"mean_retained":round(sum(len(x["keep"]) for x in compiled.values())/len(compiled),2),"backfaces_removed":sum(x["backface"] for x in compiled.values()),"occluded_removed":sum(x["occluded"] for x in compiled.values()),**packing}}
    table=sample_table();samples=cameras(g,c,zigzag);need(samples,"no valid cameras")
    sums={};failures=[];rows=[]
    def accumulate(label,mode,base,actual,equal,order_ok,lookup):
        key=f"{label}/{mode}"
        t=sums.setdefault(key,collections.Counter())
        t["frames"]+=1;t["equal"]+=equal;t["order_equal"]+=order_ok
        t["baseline_candidates"]+=base["candidate_segs"];t["compiled_candidates"]+=actual["candidate_segs"]
        t["baseline_bsp_tests"]+=base["runtime_bsp_tests"];t["compiled_bsp_tests"]+=actual["runtime_bsp_tests"]
        t["cell_lookup_tests"]+=lookup
        t["baseline_projected"]+=base["projected"];t["compiled_projected"]+=actual["projected"]
        t["baseline_projection_errors"]+=base["projection_errors"];t["compiled_projection_errors"]+=actual["projection_errors"]
        t["baseline_raster_errors"]+=base["raster_errors"];t["compiled_raster_errors"]+=actual["raster_errors"]
        t["baseline_unwritten"]+=base["unwritten_bytes"];t["compiled_unwritten"]+=actual["unwritten_bytes"]
    for label,pose,leaf,flat in samples:
        x,y,z,a=pose;base=view(lib,r,g,pose,table)
        row={"label":label,"camera":pose,"cell":leaf,"floor_material":flat,"baseline":{k:base[k] for k in ("candidate_segs","projected","runtime_bsp_tests","projection_errors","raster_errors","unwritten_bytes")}}
        for mode,v in results.items():
            cp=v["compiled"];rec=cp[leaf];keep=set(rec["keep"])
            expected=[i for i in bsp_order(g,x,y) if any(j in keep for j in range(g["subsectors"][i][1],sum(g["subsectors"][i])))]
            actual=list(ordered_leaves(g,x,y,rec["program"],{"runtime_bsp_tests":0}))
            order_ok=expected==actual
            current=view(lib,r,g,pose,table,compiled=cp)
            equal=current["state_sha256"]==base["state_sha256"] and current["projection_errors"]==base["projection_errors"] and current["raster_errors"]==base["raster_errors"]
            lookup=len(c.cells[leaf][2])
            accumulate(label,mode,base,current,equal,order_ok,lookup)
            accumulate("ALL",mode,base,current,equal,order_ok,lookup)
            row[mode]={"equal":equal,"order_equal":order_ok,**{k:current[k] for k in ("candidate_segs","projected","runtime_bsp_tests","projection_errors","raster_errors","unwritten_bytes")},"lookup_tests":lookup}
            if not equal or not order_ok:failures.append({"label":label,"camera":pose,"mode":mode,"cell":leaf,"framebuffer_equal":current["frame_sha256"]==base["frame_sha256"],"state_equal":current["state_sha256"]==base["state_sha256"],"order_equal":order_ok})
        rows.append(row)
    # Save actual preview samples on the runner, not in public artifacts.
    for label,pose,leaf,flat in samples:
        if label=="zigzag-reference":
            view(lib,r,g,pose,table,out/f"zigzag-{pose[3]}.ppm",compiled=results["backface"]["compiled"])
    report={"map":k,"samples":len(samples),"modes":{k:v["summary"] for k,v in results.items()},"groups":{k:dict(v) for k,v in sums.items()},"failures":failures,"rows":rows}
    (out/"report.json").write_text(json.dumps(report,indent=2))
    return report
def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=P);p.add_argument("library",type=P);p.add_argument("private",type=P);p.add_argument("summary",type=P);a=p.parse_args()
    tests();lib=load_native(a.library);a.private.mkdir(parents=True,exist_ok=True)
    fixture=a.private/"fixture.wad";make_fixture(fixture)
    report={"fixture":analyze(lib,WAD(fixture),"E1M1",a.private/"fixture"),"doom":{}}
    allowed={"doom1.wad","doom.wad"}
    for f in sorted(x for x in a.root.rglob("*") if x.is_file() and x.name.lower() in allowed):
        label=f.name.lower()
        if label in report["doom"]:continue
        w=WAD(f)
        if "E1M1" in w.maps():report["doom"][label]=analyze(lib,w,"E1M1",a.private/label,True)
    a.summary.write_text(json.dumps(report,indent=2))
    for label,r in [("fixture",report["fixture"]),*report["doom"].items()]:
        print("VISIBILITY "+json.dumps({"wad":label,"samples":r["samples"],"modes":r["modes"],"groups":r["groups"],"failures":r["failures"][:20],"failure_count":len(r["failures"])}),flush=True)
    if not report["doom"] or report["fixture"]["failures"] or any(r["failures"] for r in report["doom"].values()):raise SystemExit(2)
if __name__=="__main__":main()
