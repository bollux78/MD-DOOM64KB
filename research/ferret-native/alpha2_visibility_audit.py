"""Independent census of previous authenticated round5 captures.
Raw WRAM remains private. Count wall references, unique records, candidates
and actual dispatcher invocations per complete frame. Do not infer that
a WAD BSP seg equals an Alpha2 wall.
"""
import pathlib,sys,json,statistics,collections
P=pathlib.Path
def main():
    root,report=map(P,sys.argv[1:])
    results={}
    for folder in sorted(root.glob("sram*-*")):
        if not (folder/"summary.json").is_file():continue
        s=json.loads((folder/"summary.json").read_text())
        e=json.loads((folder/"events.json").read_text());w=(folder/"wram.bin").read_bytes()
        n=s["scenes"];assert len(w)==n*4*65536
        rows=[]
        for i in range(n):
            b=w[(i*4+1)*65536:(i*4+2)*65536]
            r=[];p=0x1e4
            while p+6<=0x1008:
                flag=int.from_bytes(b[p:p+2],"big")
                if flag==65535:break
                ptr=int.from_bytes(b[p+2:p+6],"big")&0xffffff
                r.append((flag,ptr));p+=6
            assert flag==65535,(folder.name,i)
            hits=collections.Counter(v[0] for v in e if v[1]==i)
            rows.append({"references":len(r),"unique_walls":len({p for f,p in r}),"conditional_refs":sum(f>1 for f,p in r),"dispatches":hits[0x7731e]+hits[0x773fc]})
        means={k:statistics.mean(r[k] for r in rows) for k in rows[0]}
        results[folder.name]={"frames":n,"means":means,"projection_calls_per_frame_300_video_frames":s["projection_calls"]/max(1,s["render_calls"]),"dispatch_calls_per_frame_300_video_frames":s["kernel_calls"]/max(1,s["render_calls"]),"min_refs":min(r["references"] for r in rows),"max_refs":max(r["references"] for r in rows),"total_map_wall_slots_reference":642,"note":"dispatch count at both validated call sites, not actual pixel coverage; previous 16 snapshots and 300-video-frame profile windows differ"}
        print("ALPHA2 VISIBILITY CENSUS "+folder.name+" "+json.dumps(results[folder.name]),flush=True)
    assert results
    report.write_text(json.dumps(results,indent=2))
if __name__=="__main__":main()
