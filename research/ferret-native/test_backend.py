"""Packed texture and DMA planner differential tests; no reference ROM needed."""
import ctypes as C, functools, json, pathlib, sys
P=pathlib.Path
sys.path.insert(0,str(P(__file__).parent.parent/"ferret-wad"))
from compiler import WAD,Resources,geometry
from render_scene import view,sample_table,load_native
from test_native import U16,U32
def main():
    root,libpath,out=map(P,sys.argv[1:])
    lib=load_native(libpath)
    class DMA(C.Structure):_fields_=[("regs",U16*5),("command",U32)]
    f=lib.fr_dma_plan;f.argtypes=[U32,U32,U32,C.POINTER(DMA)];f.restype=C.c_int
    p=DMA();assert f(0x20a600,0x20,23040,C.byref(p))==0
    assert list(p.regs)==[0x9300,0x942d,0x9500,0x9653,0x9710] and p.command==0x40200080
    for s,d,n in ((1,0,32),(0,1,32),(0,0,31),(0x1fffe,0,4),(0,65534,4),(0xffffff,0,2),(0,0,0)):
        assert f(s,d,n,C.byref(p))<0
    assert f(0xff0000,0xc000,4096,C.byref(p))==0 and p.command==0x40000083
    plan=lib.fr_plane_map;plan.argtypes=[C.POINTER(U16),C.c_size_t,U16,U16];plan.restype=C.c_size_t
    a=(U16*2048)();assert plan(a,len(a),1,2)==2048
    assert list(a[5*64:5*64+40])==list(range(0x4001,0x4029))
    assert a[22*64+39]==0x42d0 and sum(v!=0 for v in a)==720
    files=sorted(f for f in root.rglob("*") if f.is_file() and f.name.lower()=="doom1.wad");assert files
    w=WAD(files[0]);r=Resources(w);g=geometry(w,"E1M1")
    r.color=functools.lru_cache(maxsize=256)(r.color)
    r.packed_texture=functools.lru_cache(maxsize=128)(r.packed_texture)
    report=sorted(root.glob("visibility-v2/*/doom1.wad/report.json"))[-1]
    rows=json.loads(report.read_text())["rows"];table=sample_table();fail=[];counts={}
    for row in rows:
        pose=row["camera"];label=row["label"];a=view(lib,r,g,pose,table);b=view(lib,r,g,pose,table,packed=True)
        ok=all(a[k]==b[k] for k in ("state_sha256","projection_errors","raster_errors"))
        v=counts.setdefault(label,[0,0]);v[0]+=1;v[1]+=ok
        if not ok:fail.append({"camera":pose,"label":label})
    result={"packed_texture_frames":len(rows),"packed_texture_pass":len(rows)-len(fail),"groups":counts,"failures":fail,"texture_expansion_scratch_bytes":0,
            "dma_plan_pass":True,"plane_map_pass":True,"hardware_dma_validated":False,"sram16_mapping_validated":False}
    out.write_text(json.dumps(result,indent=2));print("BACKEND "+json.dumps(result),flush=True)
    if fail:sys.exit(2)
if __name__=="__main__":main()
