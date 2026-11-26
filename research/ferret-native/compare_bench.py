"""Compare R05/R06 with identical scenes and benchmark flags.
Exclude first publication (boot + SRAM probe). No diagnostic hashing in target.
"""
import json,pathlib,sys,statistics
P=pathlib.Path
def main():
    public,private=map(P,sys.argv[1:])
    a=json.loads((public/"r05-bench-mode1.json").read_text())
    b=json.loads((public/"r06-bench-mode1.json").read_text())
    assert a["pass"] and b["pass"]
    assert len(a["checks"])==len(b["checks"])==12
    rows=[]
    for x,y in zip(a["checks"],b["checks"]):
        i=x["pose"];assert i==y["pose"]
        old=(private/"r05-bench"/f"expected-tiles-{i}.bin").read_bytes()
        new=(private/"r06-bench"/f"expected-tiles-{i}.bin").read_bytes()
        assert old==new,(i,"host tile regression")
        assert x["mismatch_bytes"]==y["mismatch_bytes"]==0
        assert x["candidates"]==y["candidates"] and x["projected"]==y["projected"]
        rows.append({"pose":i,"group":"spawn" if i<4 else "zigzag","r05_video_frames":x["elapsed_video_frames"],"r06_video_frames":y["elapsed_video_frames"],"includes_boot":i==0})
    def summary(rr):
        old=sum(r["r05_video_frames"] for r in rr);new=sum(r["r06_video_frames"] for r in rr)
        return {"poses":len(rr),"r05_video_frames":old,"r06_video_frames":new,"speedup":old/new,"r05_fps_at_59_92hz":59.92*len(rr)/old,"r06_fps_at_59_92hz":59.92*len(rr)/new}
    result={"rows":rows,"all_excluding_boot":summary(rows[1:]),"zigzag":summary(rows[4:]),"spawn_excluding_boot":summary(rows[1:4]),"pixel_exact":True,"scope":"emulated video-frame intervals; same static pose sequence, WRAM, FR_BENCH, no gameplay; not directly comparable to Alpha2's different geometry and pose route"}
    (public/"benchmark-comparison.json").write_text(json.dumps(result,indent=2))
    print("R06 BENCHMARK "+json.dumps(result),flush=True)
if __name__=="__main__":main()
