"""Host-native differential test. Original ROM and snapshots are oracle inputs only.
The C core receives data views and numeric tables, never 68000 instructions to execute.
No raw resources are exported.
"""
import ctypes as C, pathlib as P, importlib.util, tempfile, json, hashlib, sys
Path=P.Path
W,H=160,72
U8,U16,I16,I32,U32=C.c_uint8,C.c_uint16,C.c_int16,C.c_int32,C.c_uint32
class Frame(C.Structure):
    _fields_=[("pixels",U8*(W*H))]+[(k,U16*W) for k in ("depth","owner","top","bottom")]
class Asset(C.Structure):
    _fields_=[("data",C.POINTER(U8)),("size",C.c_size_t),("origin",I32)]
class Job(C.Structure):
    _fields_=[(k,I32) for k in ("x0","width","inv0","inv1","scale_step","variant","textured","linear")]+[("u0",U32),("du",U32),("z",I32),("heights",I32*4),("ceiling",I32),("floor",I32)]
def load_native(path):
    lib=C.CDLL(str(path.resolve()))
    lib.fr_begin.argtypes=[C.POINTER(Frame)];lib.fr_begin.restype=None
    lib.fr_wall.argtypes=[C.POINTER(Frame),C.POINTER(Job),Asset,Asset,C.POINTER(I16),C.POINTER(U8)];lib.fr_wall.restype=C.c_int
    lib.fr_project.argtypes=[I32]*7+[C.POINTER(Job)];lib.fr_project.restype=C.c_int
    lib.fr_transform.argtypes=[I32]*6+[C.POINTER(I32),C.POINTER(I32)];lib.fr_transform.restype=None
    return lib
def diff(a,b):
    assert len(a)==len(b)
    return sum(x!=y for x,y in zip(a,b))
def custom_test(lib):
    # Entirely original texture data, two colors and a synthetic numeric sampler.
    # Solid wall with known vertical interval; must close exactly the 32 columns.
    f=Frame();f.pixels[:]=[0xa5]*(W*H);lib.fr_begin(C.byref(f))
    table=(I16*(2048*H))();sky=(U8*(W*H))()
    a=(U8*16384)(*([0x22]*16384));b=(U8*16384)(*([0x66]*16384))
    j=Job(48,32,2048,2048,0,0,1,1,0,0,0,(I32*4)(-64,64,64,64),0x11,0x33)
    assert lib.fr_wall(C.byref(f),C.byref(j),Asset(a,len(a),4096),Asset(),table,sky)==0
    before=bytes(f.pixels)
    assert 0x22 in before and all(f.depth[x]==2048 and f.top[x]==f.bottom[x]==0 for x in range(48,80))
    f=Frame();f.pixels[:]=[0xa5]*(W*H);lib.fr_begin(C.byref(f))
    assert lib.fr_wall(C.byref(f),C.byref(j),Asset(b,len(b),4096),Asset(),table,sky)==0
    after=bytes(f.pixels)
    changed=sum(x!=y for x,y in zip(before,after))
    assert changed and all(x==y or (x,y)==(0x22,0x66) for x,y in zip(before,after))
    return {"substituted_texture_bytes":changed,"original_rom_required":False}
def replay(lib,root,rom):
    from visibility import Memory,read_records
    from projection import project,transform
    table=(I16*(2048*H))()
    def s16(a):return int.from_bytes(rom[a:a+2],"big",signed=True)
    def u32(a):return int.from_bytes(rom[a:a+4],"big")
    for i in range(2048):
        addr=0x21b1c+u32(0x6d4ae+i*4)
        for y in range(H):table[i*H+y]=s16(addr+12*y+10)
    rombuf=(U8*len(rom)).from_buffer_copy(rom)
    results={}
    for rnd,runid in [(4,45645383728),(5,45657627918)]:
        folders=sorted((root/f"round{rnd}"/str(runid)).glob("sram*-*"))
        for folder in folders:
            if not (folder/"summary.json").exists():continue
            n=json.loads((folder/"summary.json").read_text())["scenes"]
            raw=(folder/"wram.bin").read_bytes()
            assert len(raw)==n*4*65536
            row={"frames":n,"native_wall_pass":0,"projection_calls":0,"projection_diff":0,"transform_calls":0,"transform_diff":0,"raster_errors":0,"pixel_diff":0,"depth_diff":0,"clip_diff":0,"first_errors":[]}
            for i in range(n):
                m=Memory(rom,raw[(i*4+1)*65536:(i*4+2)*65536])
                ref=Memory(rom,raw[(i*4+2)*65536:(i*4+3)*65536])
                f=Frame();base=m.u32(0xff2c72);f.pixels[:]=m.get(base,W*H)
                f.depth[:]=[m.u16(0xff1524+8*x) for x in range(W)]
                lib.fr_begin(C.byref(f))
                sky=(U8*(W*H))()
                for x in range(W):
                    sky[x*H:(x+1)*H]=m.get(m.u32(m.u32(0xff0fd6)+4*x),H)
                ram=(U8*65536).from_buffer(m.ram)
                def asset(ptr):
                    ptr&=0xffffff
                    if ptr>=0xff0000:return Asset(ram,65536,ptr&65535)
                    return Asset(rombuf,len(rom),ptr)
                errors=0
                for flag,wall in read_records(m):
                    v=m.u8(wall+14+(flag&1));near=m.s16(0x76ec2+16*v+8)
                    vb=m.u32(0xff1018)
                    for off in (8,10):
                        p=vb+m.s16(wall+off)
                        if not m.s16(p+4):
                            tx,tz=I32(),I32()
                            lib.fr_transform(m.s16(p),m.s16(p+2),m.s16(0xff1a32),m.s16(0xff1a30),m.s16(0xff1a2c),m.s16(0xff1a2a),C.byref(tx),C.byref(tz))
                            ex=transform(m,p);row["transform_calls"]+=1
                            if (tx.value,tz.value)!=ex:row["transform_diff"]+=1;errors+=1
                    uv=m.u32(0xff101c)+m.s16(wall+24) if near&1 else 0
                    refjob=project(m,wall,v)
                    j=Job();j.variant=v;j.z=m.s16(0xff1a2e)
                    j.heights[:]=[m.s16(wall+16+2*k) for k in range(4)]
                    j.ceiling=m.u8(wall+12);j.floor=m.u8(wall+13)
                    ret=lib.fr_project(*refjob["transformed"],near,m.s16(uv+4) if uv else 0,m.s16(uv+6) if uv else 0,C.byref(j))
                    row["projection_calls"]+=1
                    if refjob["rejected"]:
                        ok=ret==0
                    else:
                        ok=ret==1 and all(getattr(j,k)==refjob[k] for k in ("x0","width","inv0","inv1","scale_step","textured"))
                        if near&1:ok=ok and j.u0==refjob["texture_start"] and j.du==refjob["texture_step"] and bool(j.linear)==refjob["linear"]
                    if not ok:
                        errors+=1;row["projection_diff"]+=1
                        if len(row["first_errors"])<3:row["first_errors"].append({"scene":i,"stage":"projection","variant":v,"return":ret})
                        continue
                    if ret==0:continue
                    ret=lib.fr_wall(C.byref(f),C.byref(j),asset(m.u32(wall)),asset(m.u32(wall+4)),table,sky)
                    if ret:
                        errors+=1;row["raster_errors"]+=1
                        if len(row["first_errors"])<3:row["first_errors"].append({"scene":i,"stage":"raster","variant":v,"return":ret})
                pd=diff(f.pixels,ref.get(ref.u32(0xff2c72),W*H))
                dd=diff(f.depth,[ref.u16(0xff1524+8*x) for x in range(W)])
                cd=diff(f.top,[ref.u16(0xff1028+8*x) for x in range(W)])+diff(f.bottom,[ref.u16(0xff102a+8*x) for x in range(W)])
                row["pixel_diff"]+=pd;row["depth_diff"]+=dd;row["clip_diff"]+=cd
                if not(errors or pd or dd or cd):row["native_wall_pass"]+=1
                elif len(row["first_errors"])<3:row["first_errors"].append({"scene":i,"pixels":pd,"depth":dd,"clip":cd})
            results[f"r{rnd}/{folder.name}"]=row
            print(json.dumps({"case":f"r{rnd}/{folder.name}",**row}),flush=True)
    return results
def main():
    root,romfile,library,out=map(Path,sys.argv[1:])
    rom=romfile.read_bytes()
    assert hashlib.sha256(rom).hexdigest()=="47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267"
    lib=load_native(library)
    custom=custom_test(lib);print("CUSTOM ASSET "+json.dumps(custom),flush=True)
    p=Path(__file__).parent.parent/"ferret-round5"/"compare.py"
    spec=importlib.util.spec_from_file_location("r5",p)
    r5=importlib.util.module_from_spec(spec);spec.loader.exec_module(r5)
    with tempfile.TemporaryDirectory() as t:
        r5.load_models(root,Path(t))
        cases=replay(lib,root,rom)
    totals={k:sum(v[k] for v in cases.values()) for k in ("frames","native_wall_pass","projection_calls","projection_diff","transform_calls","transform_diff","raster_errors","pixel_diff","depth_diff","clip_diff")}
    out.write_text(json.dumps({"custom_asset":custom,"totals":totals,"cases":cases},indent=2))
    print("NATIVE TOTALS "+json.dumps(totals),flush=True)
    if totals["frames"]!=352 or totals["native_wall_pass"]!=352:sys.exit(2)
if __name__=="__main__":main()
