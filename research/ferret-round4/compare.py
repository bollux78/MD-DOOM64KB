"""Run earlier independent models against exact stage snapshots on the runner.
Raw evidence and ROM remain local. Only numeric summaries are exported."""
import argparse, hashlib, json, pathlib, sys, tempfile, zipfile
P=pathlib.Path
ARCHIVES={
"6a7a280b98358e920bbc06ab074ed6397cb370a94d0aeeedf9c355e0c58d35d1": ("ferret_contract.py","ferret_stage.py","raster_state.py","frame_contract.py"),
"81bf5e0e27cf3026c3f9d59447a8fae79a58307f242ca9f9f89a02af93ffa271": ("visibility.py","projection.py")
}
def load_models(root,dest):
    needed=set(ARCHIVES)
    for p in root.rglob("*.zip"):
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if digest not in needed:continue
        with zipfile.ZipFile(p) as z:
            for name in ARCHIVES[digest]:
                matches=[i for i in z.namelist() if i.rsplit("/",1)[-1]==name and (digest.startswith("6a7a") or "/modelos-anteriores/reconstruction/" in i)]
                if len(matches)!=1:raise ValueError("ambiguous archive member")
                (dest/name).write_bytes(z.read(matches[0]))
        needed.remove(digest)
    if needed:raise FileNotFoundError("Required original or round3 ZIP not found by SHA256")
    sys.path.insert(0,str(dest))

def analyze(rom,folder):
    from visibility import Memory, read_records
    from ferret_stage import stage, actor_list, visible_list_fixed
    from raster_state import render
    from frame_contract import find_cell
    class Bus(Memory):
        def __init__(self,rom,ram,sram=None):
            super().__init__(rom,ram);self.sram=bytearray(sram) if sram is not None else None
        def get(self,a,n):
            a &= 0xffffff
            if self.sram is not None and 0x200000<=a and a+n<=0x210000:return bytes(self.sram[a-0x200000:a-0x200000+n])
            return super().get(a,n)
        def put(self,a,v,n):
            addr=a&0xffffff
            if self.sram is not None and 0x200000<=addr and addr+n<=0x210000:self.sram[addr-0x200000:addr-0x200000+n]=(v&((1<<(8*n))-1)).to_bytes(n,"big");return
            if addr<0xff0000 or addr+n>0x1000000:raise ValueError("write outside captured memory")
            super().put(a,v,n)
    w=(folder/"wram.bin").read_bytes();s=(folder/"sram.bin").read_bytes() if (folder/"sram.bin").exists() else None
    events=json.loads((folder/"events.json").read_text());summary=json.loads((folder/"summary.json").read_text())
    n=summary["scenes"]
    assert len(w)==n*4*65536 and (s is None or len(s)==len(w))
    def bus(i,j):
        off=(i*4+j)*65536
        return Bus(rom,w[off:off+65536],None if s is None else s[off:off+65536])
    def diff(a,b):
        assert len(a)==len(b)
        return sum(x!=y for x,y in zip(a,b))
    rows=[]
    for i in range(n):
        row={"scene":i}
        for label,fn in [("visibility",None),("walls",None),("sprites",None)]:
            try:
                if label=="visibility":
                    b=bus(i,0);r=bus(i,1)
                    ev=[e for e in events if e[0]==0x77402 and e[1]==i]
                    if len(ev)!=1:raise ValueError("ambiguous list entry")
                    got,added,cells,saturated=visible_list_fixed(b,ev[0][14]);expected=read_records(r)
                    row[label]={"records":len(expected),"records_equal":got==expected,"actors_equal":actor_list(b)==actor_list(r),"saturated":saturated,"cell_computed":find_cell(b,b.s16(0xff1a32),b.s16(0xff1a30)),"cell_stored":(b.u32(0xff31c6)-b.u32(0xff1008))//14}
                elif label=="walls":
                    b=bus(i,1);r=bus(i,2);pixels,mask,st=render(b,read_records(b))
                    row[label]={"framebuffer_diff":diff(pixels,r.get(r.u32(0xff2c72),11520)),"written":mask.count(1),"depth_diff":diff(st["depth"],[r.u16(0xff1524+8*x) for x in range(160)]),"cliptop_diff":diff(st["cliptop"],[r.u16(0xff1028+8*x) for x in range(160)]),"clipbottom_diff":diff(st["clipbottom"],[r.u16(0xff102a+8*x) for x in range(160)])}
                else:
                    b=bus(i,2);r=bus(i,3);stats,pixels,owner,order=stage(b)
                    row[label]={**stats,"framebuffer_diff":diff(pixels,r.get(r.u32(0xff2c72),11520)),"tag_diff":diff(owner,[r.u16(0xff1526+8*x) for x in range(160)]),"actor_list_equal":order==actor_list(r),"transform_diff":sum(b.u16(a+o)!=r.u16(a+o) for a in order for o in (40,42))}
            except Exception as exc:
                # No raw exception message or memory contents exported.
                row[label]={"error_type":type(exc).__name__}
        rows.append(row)
    def passed(r,label):
        x=r[label]
        if "error_type" in x:return False
        if label=="visibility":return x["records_equal"] and x["actors_equal"]
        if label=="walls":return not any(x[k] for k in ("framebuffer_diff","depth_diff","cliptop_diff","clipbottom_diff"))
        return x["actor_list_equal"] and not any(x[k] for k in ("callbacks","framebuffer_diff","tag_diff","transform_diff"))
    return {"scenes":n,"stage_pass":{label:sum(passed(r,label) for r in rows) for label in ("visibility","walls","sprites")},"rows":rows,"note":"Each stage uses original preceding snapshot. This is not independent full-frame validation."}

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=P);p.add_argument("rom",type=P);p.add_argument("captures",type=P);p.add_argument("out",type=P);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()=="47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267"
    with tempfile.TemporaryDirectory() as t:
        load_models(a.root,P(t))
        res={}
        for folder in sorted(a.captures.glob("sram*-turn*")):
            if (folder/"summary.json").exists():res[folder.name]=analyze(rom,folder)
        a.out.write_text(json.dumps(res,indent=2))
        print(json.dumps({k:v["stage_pass"] for k,v in res.items()}))
        if len(res)!=4 or any(v["scenes"]!=16 or any(x!=16 for x in v["stage_pass"].values()) for v in res.values()):sys.exit(2)
if __name__=="__main__":main()
