"""Conservative cell+direction mask compiler for the independent renderer.
No original Alpha2 geometry/assets required. Proof against the exact Q14
projection contract (near-safe signed-word range); uncertain walls stay.
A mask bit is cleared only if every integer-degree angle in the bucket and
every position in the expanded FRV2 cell box necessarily rejects the seg.
"""
import argparse, json, pathlib, re, struct
import numpy as np
P=pathlib.Path
def arr(h,k):
    m=re.search(r"static const \w+ "+k+r"\[\d+\]\s*=\s*\{([^}]*)\}",h)
    assert m,k
    return np.fromstring(m[1].replace("\n",""),sep=",",dtype=np.int64)
def emit(f,t,k,v):
    v=np.asarray(v).reshape(-1)
    f.write(f"static const {t} {k}[{len(v)}] = {{\n")
    for i in range(0,len(v),24):f.write(",".join(map(str,v[i:i+24].tolist()))+",\n")
    f.write("};\n")
def compile_masks(scene,bins,output,report):
    h=scene.read_text()
    vs=arr(h,"sc_vertices").reshape(-1,2)
    walls=arr(h,"sc_walls").reshape(-1,14)
    trig=arr(h,"sc_trig").reshape(360,2)
    blob=arr(h,"sc_frv").astype(np.uint8).tobytes()
    magic,nc,ns,nm,nn,mb=struct.unpack_from(">4sHHHHI",blob)
    assert magic==b"FRV2" and ns==len(walls)
    stride=(ns+7)//8;assert mb==nm*stride
    base=16+12*nc
    co,si=trig.T
    dirs=(np.stack([co+si,co-si],axis=1),np.stack([si-co,co+si],axis=1),np.stack([si,co],axis=1))
    # For |dx|+|dy|<=2800, all signed-16 intermediate coordinates,
    # x+z and z-x fit: 8*2800*max(|co +/- si|)/16384 < 32766.
    assert 8*2800*max(np.abs(dirs[0]).max(),np.abs(dirs[1]).max())//16384+2<32768
    endpoints=vs[walls[:,:2]]
    extrema=[]
    for d in dirs:
        q=8*endpoints@d.T
        extrema.append((q.min(axis=1),q.max(axis=1)))
    bucket=(np.arange(360)*bins)//360
    index=[];unique={};saved=[];counts=[]
    for i in range(nc):
        x0,y0,x1,y1,mi,_=struct.unpack_from(">hhhhHH",blob,16+12*i)
        cs=np.array([[x0,y0],[x0,y1],[x1,y0],[x1,y1]],np.int64)
        safe=(np.abs(endpoints[:,:,None,:]-cs[None,None,:,:]).sum(axis=-1).max(axis=(1,2))<=2800)
        old=blob[base+mi*stride:base+(mi+1)*stride]
        keep=np.unpackbits(np.frombuffer(old,dtype=np.uint8),bitorder="little")[:ns].astype(bool)
        ranges=[]
        for d,(mn,mx) in zip(dirs,extrema):
            cq=8*cs@d.T
            ranges.append((mn-cq.max(axis=0),mx-cq.min(axis=0)))
        (lmin,lmax),(rmin,rmax),(zmin,zmax)=ranges
        # floor(A)+floor(B) <= floor(A+B), >= floor(A+B)-1.
        # Left rejection is unconditional. Right/near require all earlier
        # clips to be no-ops, so integer clipping cannot invalidate the proof.
        reject=(lmax<0)|((lmin>=16384)&(rmax<0))|((lmin>=16384)&(rmin>=16384)&(zmax<walls[:,3,None]*16384))
        reject &= safe[:,None]
        for b in range(bins):
            off=reject[:,bucket==b].all(axis=1)
            new=keep&~off
            mask=np.packbits(new,bitorder="little").tobytes()
            assert len(mask)==stride
            if mask not in unique:unique[mask]=len(saved);saved.append(mask)
            index.append(unique[mask]);counts.append((int(keep.sum()),int(new.sum())))
    assert len(saved)<65536
    blob=np.frombuffer(b"".join(saved),dtype=np.uint8)
    with output.open("w") as f:
        f.write(f"#define SC_ANG_BINS {bins}\n#define SC_ANG_STRIDE {stride}\n#define SC_ANG_CELLS {nc}\n")
        emit(f,"uint8_t","sc_ang_bucket",bucket);emit(f,"uint16_t","sc_ang_index",index);emit(f,"uint8_t","sc_ang_masks",blob)
    old,new=np.sum(counts,axis=0).tolist()
    result={"cells":nc,"segs":ns,"bins":bins,"unique_masks":len(saved),"bytes":len(blob)+2*len(index)+360,"offline_candidates_all_cells_buckets":old,"angle_candidates_all_cells_buckets":new,"offline_reduction_percent":100*(old-new)/old,"proof":"fixed Q14 endpoint extrema over expanded FRV2 cell boxes; retain all unsafe/wrap cases; only guaranteed reject before clipping"}
    report.write_text(json.dumps(result,indent=2));print("ANGULAR MASK "+json.dumps(result),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("scene",type=P);p.add_argument("output",type=P);p.add_argument("report",type=P);p.add_argument("--bins",type=int,choices=(8,16,32),default=16);a=p.parse_args()
    compile_masks(a.scene,a.bins,a.output,a.report)
