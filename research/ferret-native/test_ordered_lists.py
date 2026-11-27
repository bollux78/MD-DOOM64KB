"""Differential audit against unmodified FRV2: all complete raster state,
all counters, camera leaf, and runtime conditional test count must match."""
import ctypes as C,collections,json,pathlib,random,struct,sys
from compile_ordered_lists import arr
from test_demo import Stats
P=pathlib.Path
def load(d):
    lib=C.CDLL(str(d/"demo-host.so"))
    lib.fr_demo_state_size.restype=C.c_uint
    n=lib.fr_demo_state_size()
    assert 11520<=n<65536
    f=lib.fr_demo_camera
    f.argtypes=[C.c_int]*4+[C.POINTER(Stats),C.POINTER(C.c_uint8)];f.restype=C.c_int
    def run(p):
        stats=Stats();state=(C.c_uint8*n)()
        rc=f(*p,C.byref(stats),state)
        return rc,bytes(state),tuple(getattr(stats,k) for k,_ in stats._fields_)
    return lib,run
def main():
    a,b,o=map(P,sys.argv[1:]);la,ga=load(a);lb,gb=load(b)
    h=(b/"scene.h").read_text()
    planes=arr(h,"sc_planes");children=arr(h,"sc_children")
    floors=arr(h,"sc_floor");ceils=arr(h,"sc_ceiling")
    blob=bytes(arr(h,"sc_frv"));nc=struct.unpack_from(">H",blob,4)[0]
    assert nc==len(floors)==len(ceils)
    def leaf(x,y):
        q=len(planes)//4-1 if planes else 32768
        while not q&32768:
            u,v,dx,dy=planes[q*4:q*4+4]
            q=children[q*2+int(dx*(y-v)>=dy*(x-u))]
        return q&32767
    poses=[]
    raw=arr(h,"sc_poses")
    for i in range(0,len(raw),4):poses.append(("reference",tuple(raw[i:i+4])))
    for label,x,y,z in [("spawn",1056,-3616,41),("zigzag",2980,-3286,17)]:
        if leaf(x,y)<nc:
            for deg in range(360):poses.append((label,(x,y,z,deg)))
    rng=random.Random(20261126)
    for i in range(nc):
        x0,y0,x1,y1,_,_=struct.unpack_from(">hhhhHH",blob,16+12*i)
        if ceils[i]-floors[i]<42:continue
        points=[((x0+x1)//2,(y0+y1)//2)]
        points += [(rng.randint(x0,x1),rng.randint(y0,y1)) for _ in range(24)]
        accepted=[]
        for x,y in points:
            if leaf(x,y)==i and (x,y) not in accepted:accepted.append((x,y))
            if len(accepted)==3:break
        for x,y in accepted:
            for z in (floors[i]+41,):
                for deg in [0,45,90,135,180,225,270,315,rng.randrange(360),rng.randrange(360)]:
                    poses.append(("distributed",(x,y,z,deg)))
    totals=collections.defaultdict(collections.Counter)
    bad=[]
    for label,p in poses:
        x,y=ga(p),gb(p);t=totals[label];t["cases"]+=1
        if x[0] or y[0]:
            t["invalid"]+=1
            if x[0]!=y[0]:bad.append({"pose":p,"rc":[x[0],y[0]]})
            continue
        equal=x==y;t["matched"]+=equal
        if not equal and len(bad)<20:
            bad.append({"pose":p,"state_byte_differences":sum(u!=v for u,v in zip(x[1],y[1])),"stats":[x[2],y[2]]})
    r={"groups":{k:dict(v) for k,v in totals.items()},"cases":len(poses),"matched":sum(t["matched"] for t in totals.values()),"mismatches":sum(t["cases"]-t["matched"]-t["invalid"] for t in totals.values()),"first_failures":bad}
    r["pass"]=not bad and r["mismatches"]==0 and r["matched"]>=1000
    o.write_text(json.dumps(r,indent=2));print("ORDERED LIST DIFF "+json.dumps(r),flush=True);assert r["pass"]
if __name__=="__main__":main()
