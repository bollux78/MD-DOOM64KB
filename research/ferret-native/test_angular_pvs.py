"""Differential test of angle masks on thousands of cameras.
Compare complete framebuffer, depth, tags and top/bottom, not just hashes.
"""
import ctypes as C,json,pathlib,random,struct,sys,collections
from angular_pvs import arr
from test_demo import Stats
P=pathlib.Path
def load(p):
    lib=C.CDLL(str(p/"demo-host.so"));f=lib.fr_demo_camera
    f.argtypes=[C.c_int]*4+[C.POINTER(Stats),C.POINTER(C.c_uint8),C.POINTER(C.c_uint32)];f.restype=C.c_int
    def go(p):
        s=Stats();state=(C.c_uint8*12800)();calls=C.c_uint32()
        rc=f(*p,C.byref(s),state,C.byref(calls))
        return rc,bytes(state),{k:getattr(s,k) for k,_ in s._fields_},calls.value
    return lib,go
def main():
    old,new,out=map(P,sys.argv[1:]);a,go=load(old);b,gn=load(new)
    h=(new/"scene.h").read_text()
    planes=arr(h,"sc_planes").reshape(-1,4).tolist();children=arr(h,"sc_children").reshape(-1,2).tolist()
    floors=arr(h,"sc_floor").tolist();ceils=arr(h,"sc_ceiling").tolist()
    blob=bytes(arr(h,"sc_frv").tolist())
    nc=struct.unpack_from(">H",blob,4)[0]
    def leaf(x,y):
        q=len(planes)-1 if planes else 32768
        while not q&32768:
            u,v,dx,dy=planes[q];q=children[q][int(dx*(y-v)>=dy*(x-u))]
        return q&32767
    rng=random.Random(20261126)
    poses=[]
    for label,x,y,z in [("spawn",1056,-3616,41),("zigzag",2980,-3286,17)]:
        for deg in range(360):poses.append((label,(x,y,z,deg)))
    # Test the complete heading range at the exact reference locations.
    # Include independent cell samples and angle-bin boundaries.
    for i in range(nc):
        x0,y0,x1,y1,_,_=struct.unpack_from(">hhhhHH",blob,16+12*i)
        if ceils[i]-floors[i]<42:continue
        points=[((x0+x1)//2,(y0+y1)//2)]
        for _ in range(24):points.append((rng.randint(x0,x1),rng.randint(y0,y1)))
        pts=[]
        for x,y in points:
            if leaf(x,y)==i and (x,y) not in pts:pts.append((x,y))
            if len(pts)==3:break
        for x,y in pts:
            for deg in [0,45,90,135,180,225,270,315,rng.randrange(360),rng.randrange(360)]:
                poses.append(("distributed",(x,y,floors[i]+41,deg)))
    totals=collections.defaultdict(lambda:collections.Counter())
    failures=[];rows=[]
    for label,p in poses:
        ra,sa,ma,ca=go(p);rb,sb,mb,cb=gn(p)
        t=totals[label];t["cases"]+=1
        if ra or rb:
            if ra!=rb:failures.append({"label":label,"pose":p,"rc":[ra,rb]})
            t["outside_or_invalid"]+=1;continue
        eq=sa==sb and all(ma[k]==mb[k] for k in ("projected","errors","closed","leaf","tests","hash"))
        if not eq:
            failures.append({"label":label,"pose":p,"state_bytes_diff":sum(x!=y for x,y in zip(sa,sb)),"before":ma,"after":mb})
        t["pass"]+=eq;t["baseline_candidates"]+=ma["candidates"];t["angle_candidates"]+=mb["candidates"]
        t["baseline_projection_calls"]+=ca;t["angle_projection_calls"]+=cb;t["projected"]+=ma["projected"]
        if label in ("spawn","zigzag") and p[3]%90==0:
            rows.append({"label":label,"camera":p,"baseline_candidates":ma["candidates"],"angle_candidates":mb["candidates"],"baseline_projection_calls":ca,"angle_projection_calls":cb,"projected":ma["projected"],"equal":eq})
    result={"summary":{k:dict(v) for k,v in totals.items()},"reference_cardinal_poses":rows,"failures":len(failures),"first_failures":failures[:8],"pass":not failures and sum(v["pass"] for v in totals.values())>=1000}
    out.write_text(json.dumps(result,indent=2));print("ANGULAR DIFFERENTIAL "+json.dumps(result),flush=True)
    assert result["pass"]
if __name__=="__main__":main()
