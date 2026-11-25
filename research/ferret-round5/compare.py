"""Run earlier independent models against exact stage snapshots on the runner.
Raw evidence and ROM remain local. Only numeric summaries are exported."""
import argparse, hashlib, json, pathlib, sys, tempfile, zipfile, base64, zlib
P=pathlib.Path
HASHES={
"ferret_contract.py":"75105b0946eab58b9447c9ba0f254fa00dcad3d38ebcc14ed434d0342ab0e2fb",
"ferret_stage.py":"b8d92efe405370094680f92be170518555073f1813469f95ba5019cf65939100",
"raster_state.py":"39e55238a008c1babaec5a7f163b5de8d211699a56337e715d9f1a92deb6e604",
"frame_contract.py":"bcf2413001a007729c49e438673ddbe1cd80453f0b43db2897e7402f2c0ef9d5",
"kernel_cpu.py":"ed0d6b83127020c99cf4120970bfe5c809b35c7a4474c59c38f36f0b0f53f2a7",
"visibility.py":"9ba0e64d903d9ccf1383778052199d04df7dcaac331cd3fcb9cf3d15fbaf15f4",
"projection.py":"5bd1120c423d15967219f1518db2e18de5c26dc0417e72d8f2d477453690b46c"
}
def load_models(root,dest):
    needed=set(HASHES)
    def accept(name,data):
        if name in needed and hashlib.sha256(data).hexdigest()==HASHES[name]:
            (dest/name).write_bytes(data);needed.remove(name)
    bundled=json.loads((P(__file__).parent.parent/"ferret-round4"/"round3-models.json").read_text())
    for name,encoded in bundled.items():
        data=zlib.decompress(base64.b64decode(encoded,validate=True))
        if name not in HASHES or hashlib.sha256(data).hexdigest()!=HASHES[name]:
            raise ValueError("Bundled model hash mismatch: "+name)
        accept(name,data)
    for p in root.rglob("*"):
        if not needed:break
        if not p.is_file():continue
        if p.name in needed and p.stat().st_size<100000:
            accept(p.name,p.read_bytes())
        elif p.suffix.lower()==".zip":
            try:
                with zipfile.ZipFile(p) as z:
                    for info in z.infolist():
                        name=info.filename.rsplit("/",1)[-1]
                        if name in needed and info.file_size<100000:accept(name,z.read(info))
            except zipfile.BadZipFile:continue
    print("Verified model members:",sorted(set(HASHES)-needed),flush=True)
    if needed:raise FileNotFoundError("Missing verified model members: "+", ".join(sorted(needed)))
    sys.path.insert(0,str(dest))

def analyze(rom,folder):
    from visibility import Memory, read_records
    from ferret_stage import stage, actor_list, visible_list_fixed
    from raster_state import render
    from frame_contract import find_cell,begin_frame,build_setup_tables
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
    prev=None
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
                import traceback
                with (folder/"compare-errors.log").open("a") as log: traceback.print_exc(file=log)
        # No original list-return or wall-return state enters the chained model.
        try:
            b=bus(i,0); r=bus(i,3); base=b.u32(0xff2c72)
            initial=b.get(base,11520)
            initial_depth=[b.u16(0xff1524+8*x) for x in range(160)]
            incoming={"same_buffer":False,"framebuffer_diff":None,"depth_diff":None}
            if prev is not None and prev[0]==base:
                incoming={"same_buffer":True,"framebuffer_diff":diff(prev[1],initial),"depth_diff":diff(prev[2],initial_depth)}
                # Explicitly test retained buffers from preceding predicted stage; do not call
                # intervening game state independent, and report differences before replay.
                b.ram[(base&65535):(base&65535)+11520]=prev[1]
                for x,v in enumerate(prev[2]):b.put(0xff1524+8*x,v,2)
            stored=b.u32(0xff31c6)
            stream=b.u32(stored)
            ev=[e for e in events if e[0]==0x77402 and e[1]==i]
            if len(ev)!=1:raise ValueError("ambiguous list entry")
            stream_match=stream==ev[0][14]
            build_setup_tables(b)
            begin_frame(b,base,b.u16(0xff31cc),b.u16(0xff2368))
            got,added,cells,saturated=visible_list_fixed(b,stream)
            pix,mask,st=render(b,got)
            b.ram[(base&65535):(base&65535)+11520]=pix
            for x in range(160):
                b.put(0xff1524+8*x,st["depth"][x],2)
                b.put(0xff1028+8*x,st["cliptop"][x],2)
                b.put(0xff102a+8*x,st["clipbottom"][x],2)
            stats,final,owner,order=stage(b)
            row["chain"]={"stream_match":stream_match,"incoming":incoming,"framebuffer_diff":diff(final,r.get(r.u32(0xff2c72),11520)),"tag_diff":diff(owner,[r.u16(0xff1526+8*x) for x in range(160)]),"actor_list_equal":order==actor_list(r),"depth_diff":diff(st["depth"],[r.u16(0xff1524+8*x) for x in range(160)]),"callbacks":stats["callbacks"]}
            prev=(base,bytes(final),st["depth"])
        except Exception as exc:
            row["chain"]={"error_type":type(exc).__name__}
            prev=None
            import traceback
            with (folder/"chain-errors.log").open("a") as log:traceback.print_exc(file=log)
        rows.append(row)
    def passed(r,label):
        x=r[label]
        if "error_type" in x:return False
        if label=="chain":return x["stream_match"] and x["actor_list_equal"] and not any(x[k] for k in ("framebuffer_diff","depth_diff","tag_diff","callbacks"))
        if label=="visibility":return x["records_equal"] and x["actors_equal"]
        if label=="walls":return not any(x[k] for k in ("framebuffer_diff","depth_diff","cliptop_diff","clipbottom_diff"))
        return x["actor_list_equal"] and not any(x[k] for k in ("callbacks","framebuffer_diff","tag_diff","transform_diff"))
    return {"scenes":n,"stage_pass":{label:sum(passed(r,label) for r in rows) for label in ("visibility","walls","sprites","chain")},"rows":rows,"note":"Separate stages seed original preceding snapshot. Chain seeds game state at list entry, carries previous predicted pixels/depth when buffer matches, and reconstructs list, walls and sprites without intermediate snapshots. Not a standalone game or VDP validation."}

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=P);p.add_argument("rom",type=P);p.add_argument("captures",type=P);p.add_argument("out",type=P);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()=="47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267"
    with tempfile.TemporaryDirectory() as t:
        load_models(a.root,P(t))
        res={}
        for folder in sorted(a.captures.glob("sram*-*")):
            if (folder/"summary.json").exists():res[folder.name]=analyze(rom,folder)
        a.out.write_text(json.dumps(res,indent=2))
        print(json.dumps({k:{"scenes":v["scenes"],"stage_pass":v["stage_pass"],"chain_errors":[r["chain"] for r in v["rows"] if "error_type" in r["chain"] or r["chain"].get("framebuffer_diff",0)]} for k,v in res.items()}),flush=True)
        if not res or any(v["scenes"]==0 for v in res.values()):sys.exit(2) # divergences are evidence, not workflow infrastructure failure
if __name__=="__main__":main()
