"""Check MAME screen publication and CPU mailbox against host results."""
import json,pathlib,sys
P=pathlib.Path
def main():
    src,log,out=map(P,sys.argv[1:])
    if src.is_dir():
        from test_demo import host
        expected=host(src)
    else:expected=json.loads(src.read_text())
    records=[];seen=set()
    for line in log.read_text(errors="replace").splitlines():
        if not line.startswith("PUBLISHED "):continue
        t=line.split()
        if len(t)!=21:continue
        frame=int(t[1]);m=[int(x,16) for x in t[2:19]];colors,nonblack=map(int,t[19:21])
        i=m[4]
        if i in seen or i>=len(expected):continue
        e=expected[i];seen.add(i)
        match=m[0]==0x46523031 and m[5]==e["hash"] and m[6]==e["tiles_hash"] and m[7]==e["candidates"] and m[8]==e["projected"] and m[9]==e["errors"] and m[10]==e["closed"] and m[12]==0
        records.append({"pose":i,"frame":frame,"match":match,"colors":colors,"nonblack_samples":nonblack,"sram":m[11],"mailbox":m})
    result={"expected":len(expected),"matched":sum(r["match"] for r in records),"records":records,"pass":len(records)==len(expected) and all(r["match"] for r in records) and any(r["colors"]>=2 and r["nonblack_samples"]>0 for r in records),"scope":"CPU mailbox hash and displayed pixel diversity; not direct VRAM hash"}
    out.write_text(json.dumps(result,indent=2));print("MAME "+json.dumps(result),flush=True)
    if not result["pass"]:sys.exit(2)
if __name__=="__main__":main()
