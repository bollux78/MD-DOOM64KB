"""End-to-end independent rendering smoke test, from WAD to native C framebuffer.
This is a BSP fallback and a generated approximation of the vertical sample table,
not a reproduction of Ferret's offline visibility compiler.
"""
import argparse, ctypes as C, json, math, pathlib, struct, sys, hashlib
from compiler import WAD,Resources,geometry,bsp_order,need,name,summary
P=pathlib.Path
sys.path.insert(0,str(P(__file__).parent.parent/"ferret-native"))
from test_native import Frame,Asset,Job,U8,I16,I32,W,H,load_native
def make_fixture(p):
    # A wholly original, simple four-wall room.
    def rec(fmt,rs):return b"".join(struct.pack(fmt,*r) for r in rs)
    palette=bytes(v for i in range(256) for v in (i,(i*3)%256,(i*7)%256))
    cols=[bytes([0,64,0])+bytes((x*3+y*5)%256 for y in range(64))+b"\0\xff" for x in range(64)]
    pat=struct.pack("<hhhh",64,64,32,64)+rec("<I",[(8+64*4+i*len(cols[0]),) for i in range(64)])+b"".join(cols)
    tex=struct.pack("<II",1,8)+struct.pack("<8sIhhIHhhHhh",b"WALL",0,64,64,0,1,0,0,0,0,0)
    vertices=[(-128,-128),(-128,128),(128,128),(128,-128)]
    # clockwise; each right sidedef faces the room.
    entries=[("PLAYPAL",palette),("PNAMES",struct.pack("<I8s",1,b"PAT")),("TEXTURE1",tex),("PAT",pat),
             ("F_START",b""),("FLAT",bytes([80])*4096),("F_END",b""),("S_START",b""),("TESTA0",pat),("S_END",b""),
             ("E1M1",b""),("THINGS",rec("<hhHHH",[(0,0,0,1,7)])),
             ("LINEDEFS",rec("<HHHHHHH",[(i,(i+1)%4,1,0,0,i,65535) for i in range(4)])),
             ("SIDEDEFS",rec("<hh8s8s8sH",[(0,0,b"-",b"-",b"WALL",0)]*4)),
             ("VERTEXES",rec("<hh",vertices)),("SEGS",rec("<HHHHHH",[(i,(i+1)%4,0,i,0,0) for i in range(4)])),
             ("SSECTORS",rec("<HH",[(4,0)])),("NODES",b""),
             ("SECTORS",rec("<hh8s8shhh",[(0,128,b"FLAT",b"FLAT",160,0,0)])),("REJECT",b"\0"),("BLOCKMAP",b"")]
    data=bytearray(b"PWAD"+bytes(8));directory=[]
    for k,b in entries:directory.append((len(data),len(b),k.encode()));data.extend(b)
    off=len(data);data.extend(rec("<II8s",directory));struct.pack_into("<II",data,4,len(entries),off);p.write_bytes(data)
def bundle(wad,r,g,k,out):
    out.mkdir(parents=True,exist_ok=True)
    # Explicit endian-independent metadata, raw byte assets; not target ROM layout.
    textures={}
    for i,key in enumerate(sorted(r.defs)):
        data,origin=r.packed_texture(key);fn=f"texture-{i:04}.bin";(out/fn).write_bytes(data)
        textures[key]={"file":fn,"origin":origin,"size":len(data)}
    sprites={}
    for i,key in enumerate(sorted(r.sprites)):
        s=r.sprite(key);fn=f"sprite-{i:04}.bin";data=s.pop("pixels");(out/fn).write_bytes(data)
        sprites[key]={**s,"file":fn,"size":len(data)}
    def encode(x):
        if isinstance(x,bytes):return name(x)
        raise TypeError(type(x))
    (out/"scene.json").write_text(json.dumps({"format":"FR-WAD-0","map":k,"palette":r.palette,"textures":textures,"sprites":sprites,"geometry":g},default=encode,separators=(",",":")))
    return len(textures),len(sprites)
def sample_table():
    # Numeric reference, independently generated; exact scaler quantization still open.
    a=(I16*(2048*H))()
    for i in range(2048):
        for y in range(H):a[i*H+y]=((y-35)*128)//max(i,1)-1
    return a
def view(lib,r,g,camera,table,output=None,compiled=None,packed=False):
    x,y,z,angle=camera
    si=round(math.sin(math.radians(90-angle))*16384);co=round(math.cos(math.radians(90-angle))*16384)
    # Camera +X = 0 degrees, positive angle turns towards +Y.
    f=Frame();f.pixels[:]=[0xa5]*(W*H);lib.fr_begin(C.byref(f))
    sky=(U8*(W*H))()
    skykey=next((k for k in ("SKY1","SKY2","SKY3","SKY4") if k in r.defs),None)
    if skykey:
        sw,sh,sr=r.texture(skykey)
        for xx in range(W):
            for yy in range(H):sky[xx*H+yy]=sr[min(sh-1,yy*sh//H)][(int(angle*sw/360)+xx*sw//(W*4))%sw]
    cache={};fallback=set();masked=0;unsupported=0
    wall=lib.fr_wall_packed if packed else lib.fr_wall
    if packed:
        wall.argtypes=lib.fr_wall.argtypes;wall.restype=lib.fr_wall.restype
    def packed_bytes(b):
        tile=b[8192:16384]
        return bytes((tile[i]&240)|(tile[i+1]&15) for i in range(0,8192,2))
    def tex(k,origin):
        if k not in r.defs:
            fallback.add(k);key=("?",0)
            if key not in cache:
                b=bytes([0x55])*24576
                if packed:b=packed_bytes(b)
                cache[key]=(U8*len(b)).from_buffer_copy(b),8192
        else:
            key=(k,origin)
            if key not in cache:
                b,o=r.packed_texture(k,origin)
                if packed:b=packed_bytes(b)
                cache[key]=(U8*len(b)).from_buffer_copy(b),o
        a,o=cache[key];return Asset(a,len(a),o)
    stats={"candidate_segs":0,"projected":0,"closed_columns":0,"projection_errors":0,"raster_errors":0}
    stats["runtime_bsp_tests"]=0
    keep,order=None,None
    if compiled is not None:
        from visibility_compile import selection
        keep,order=selection(g,x,y,compiled,stats)
    if order is None:
        # Count actual visited branch decisions, including traversal before early closure.
        def baseline():
            stack=[len(g["nodes"])-1 if g["nodes"] else 32768]
            while stack:
                i=stack.pop()
                if i&32768:yield i&32767;continue
                a,b,dx,dy,*rest=g["nodes"][i]
                side=int((x-a)*dy<=(y-b)*dx)
                stats["runtime_bsp_tests"]+=1
                c=rest[-2:];stack.extend((c[1-side],c[side]))
        order=baseline()
    for leaf in order:
        if all(a==b==0 for a,b in zip(f.top,f.bottom)):break
        n,a=g["subsectors"][leaf]
        for segid in range(a,a+n):
            if keep is not None and segid not in keep:continue
            v0,v1,_,lid,d,ofs=g["segs"][segid]
            stats["candidate_segs"]+=1
            l=g["lines"][lid];side=l[5+d];other=l[6-d]
            if side==65535:continue
            sd=g["sides"][side];front=g["sectors"][sd[-1]]
            floor,ceil=front[:2];skyf=name(front[3])=="F_SKY1"
            back=g["sectors"][g["sides"][other][-1]] if other!=65535 else None
            solid=back is None or max(floor,back[0])>=min(ceil,back[1])
            if not solid and name(sd[4])!="-":masked+=1
            if floor>=ceil:unsupported+=1;continue
            if solid:
                variant=2 if skyf else 0
                heights=(-ceil,-floor,-floor,-floor)
                uk=name(sd[4]);lk="-"
                if uk=="-":uk=next((name(t) for t in sd[2:4] if name(t)!="-"),"-")
                textured=True
            else:
                bf,bc=back[:2]
                upper=bc<ceil and not(skyf and name(back[3])=="F_SKY1")
                lower=bf>floor
                variant=({(False,False):13,(True,False):16,(False,True):14,(True,True):17} if skyf else {(False,False):7,(True,False):10,(False,True):8,(True,True):11})[(upper,lower)]
                heights=(-ceil,-min(ceil,bc) if upper else -ceil,-max(floor,bf),-floor)
                uk,lk=name(sd[2]),name(sd[3]);textured=upper or lower
            coords=[]
            for vx,vy in (g["vertices"][v0],g["vertices"][v1]):
                tx,tz=I32(),I32();lib.fr_transform(vx,vy,x*8,y*8,co,si,C.byref(tx),C.byref(tz));coords.extend((tx.value,tz.value))
            length=round(math.dist(g["vertices"][v0],g["vertices"][v1]))
            u=(sd[0]+ofs)//2;u0=u%64;u1=u0+length//2
            j=Job();j.variant=variant;j.z=-z;j.heights[:]=heights;j.ceiling=r.color(name(front[3]));j.floor=r.color(name(front[2]))
            ret=lib.fr_project(*coords,161 if textured else 160,u0,u1,C.byref(j))
            if ret<0:stats["projection_errors"]+=1;continue
            if not ret:continue
            stats["projected"]+=1
            # Height origin compensates the native camera-dependent byte offset.
            au=tex(uk,ceil+sd[1]) if textured else Asset();al=tex(lk,(back[0] if back else floor)+sd[1]) if textured else Asset()
            if wall(C.byref(f),C.byref(j),au,al,table,sky):stats["raster_errors"]+=1
    stats.update(closed_columns=sum(a==b==0 for a,b in zip(f.top,f.bottom)),written_bytes=sum(v!=0xa5 for v in f.pixels),unwritten_bytes=sum(v==0xa5 for v in f.pixels),masked_candidates=masked,unsupported_sectors=unsupported,missing_materials=len(fallback),frame_sha256=hashlib.sha256(bytes(f.pixels)).hexdigest(),state_sha256=hashlib.sha256(bytes(f.pixels)+struct.pack(">480H",*f.depth,*f.top,*f.bottom)).hexdigest())
    if output:
        with output.open("wb") as fp:
            fp.write(f"P6\n{W} {H}\n255\n".encode())
            for yy in range(H):
                for xx in range(W):
                    v=f.pixels[(xx//2)*144+(xx&1)+yy*2]
                    fp.write(bytes((255,0,255) if v==0xa5 else r.palette[v>>4]))
    return stats
def run_one(lib,p,out,fixture=False):
    wad=WAD(p);r=Resources(wad);stats=summary(wad)
    k="E1M1" if "E1M1" in wad.maps() else wad.maps()[0];g=geometry(wad,k)
    ntex,nsprite=bundle(wad,r,g,k,out)
    start=next(t for t in g["things"] if t[3]==1);x,y,a=start[:3]
    # Locate starting sector through the closest BSP leaf, not a hardcoded z.
    leaf=next(bsp_order(g,x,y));n,first=g["subsectors"][leaf];seg=g["segs"][first];line=g["lines"][seg[3]]
    floor=g["sectors"][g["sides"][line[5+seg[4]]][-1]][0]
    table=sample_table()
    views=[view(lib,r,g,(x,y,floor+41,a+angle),table,out/f"view-{angle}.ppm") for angle in (0,90,180,270)]
    if fixture:
        assert all(v["written_bytes"]==W*H and v["closed_columns"]==W and not v["projection_errors"] and not v["raster_errors"] for v in views),views
    return {"wad_kind":wad.data[:4].decode(),"fixture":fixture,"resources":stats,"bundle":{"textures":ntex,"sprites":nsprite},"views":views,"reference_rom_used":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=P);p.add_argument("library",type=P);p.add_argument("private",type=P);p.add_argument("summary",type=P);a=p.parse_args()
    a.private.mkdir(parents=True,exist_ok=True);lib=load_native(a.library)
    fixture=a.private/"fixture.wad";make_fixture(fixture)
    result={"fixture":run_one(lib,fixture,a.private/"fixture",True),"iwads":{},"limitations":["BSP fallback not Ferret PVS","approximate generated vertical scaler","flat colors and provisional palette","masked midtextures and moving geometry not yet rendered","no sprite scene placement"]}
    allowed={"doom1.wad","doom.wad","doom2.wad","freedoom1.wad","freedoom2.wad"}
    for i,p in enumerate(sorted(x for x in a.root.rglob("*") if x.is_file() and x.name.lower() in allowed)):
        label=p.name.lower()
        if label in result["iwads"]:continue
        try:result["iwads"][label]=run_one(lib,p,a.private/f"iwad-{i}")
        except Exception as e:
            import traceback
            (a.private/f"iwad-{i}-errors.log").write_text(traceback.format_exc())
            result["iwads"][label]={"error_type":type(e).__name__}
    a.summary.write_text(json.dumps(result,indent=2))
    print("WAD COMPILER "+json.dumps(result),flush=True)
    if not result["iwads"] or any("error_type" in v for v in result["iwads"].values()):sys.exit(2)
if __name__=="__main__":main()
