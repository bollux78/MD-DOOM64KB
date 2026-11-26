"""Compare geometry/coverage between legacy and art builds and quantify pair usage.
All generated images and raw tile data are private. No screenshot likeness claim.
"""
import pathlib,json,sys,collections
from test_demo import host
P=pathlib.Path
def stats(b):
    return {"bytes":len(b),"distinct_pairs":len(set(b)),"distinct_indices":len({v for x in b for v in (x>>4,x&15)}),"mixed_pair_fraction":sum((x>>4)!=(x&15) for x in b)/max(1,len(b))}
def main():
    old,new,refroot,report=map(P,sys.argv[1:])
    a,b=host(old),host(new);assert len(a)==len(b)
    keys=("candidates","projected","errors","closed","leaf","tests")
    rows=[]
    for i,(x,y) in enumerate(zip(a,b)):
        same=all(x[k]==y[k] for k in keys)
        rows.append({"pose":i,"same_geometry":same,"legacy":stats((old/f"expected-tiles-{i}.bin").read_bytes()),"art":stats((new/f"expected-tiles-{i}.bin").read_bytes())})
    refs=[]
    if refroot.is_dir():
        for f in sorted(refroot.glob("sram0-*/wram.bin")):
            raw=f.read_bytes();frames=[]
            for i in range(len(raw)//(4*65536)):
                ram=raw[(4*i+3)*65536:(4*i+4)*65536]
                addr=int.from_bytes(ram[0x2c72:0x2c76],"big")&0xffffff
                if 0xff0000<=addr<=0x1000000-11520:
                    frames.append(stats(ram[addr-0xff0000:addr-0xff0000+11520]))
            if frames:refs.append({"scene":f.parent.name,"frames":len(frames),"mean_mixed_pair_fraction":sum(v["mixed_pair_fraction"] for v in frames)/len(frames),"mean_distinct_pairs":sum(v["distinct_pairs"] for v in frames)/len(frames)})
    result={"poses":rows,"alpha2_pair_statistics":refs,"pass":all(r["same_geometry"] for r in rows) and all(v["errors"]==0 for v in b) and any(r["art"]["mixed_pair_fraction"]>.05 for r in rows),"scope":"geometry counters and two-color byte statistics; not exact color or visual similarity to Alpha2"}
    report.write_text(json.dumps(result,indent=2));print("ART COMPARISON "+json.dumps(result),flush=True)
    if not result["pass"]:sys.exit(2)
if __name__=="__main__":main()
