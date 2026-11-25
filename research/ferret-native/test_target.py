"""Independent target preparation tests. ROM data is only used as a numeric oracle
for the scaler investigation; no ROM bytes, WAD assets or screenshots published."""
import argparse, ctypes as C, hashlib, json, pathlib, random, struct, sys, collections, math
P=pathlib.Path
sys.path.insert(0,str(P(__file__).parent.parent/"ferret-wad"))
sys.path.insert(0,str(P(__file__).parent))
from compiler import WAD, Resources, geometry
from visibility_compile import read_dag, find_leaf
from test_native import U8,U16,U32,I16,load_native
def cbuf(b):return (U8*len(b)).from_buffer_copy(b)
def visibility(lib,root,wad):
    g=geometry(wad,"E1M1")
    candidates=sorted(root.glob("visibility-v2/*/doom1.wad/report.json"))
    assert candidates,"no validated FRV2 reports"
    report=json.loads(candidates[-1].read_text())
    planes=(I16*(4*len(g["nodes"])))(*(x for n in g["nodes"] for x in n[:4]))
    fn=lib.frv_collect;fn.argtypes=[C.POINTER(U8),C.c_size_t,U16,I16,I16,C.POINTER(I16),U16,C.POINTER(U16),U16,C.POINTER(U8),C.POINTER(U32)];fn.restype=C.c_int
    result={}
    for mode in ("backface","occlusion","occlusion96"):
        blob=(candidates[-1].parent/f"{mode}.frv2").read_bytes()
        b=cbuf(blob);cell,walk=read_dag(g,blob);leaves=(U16*len(g["subsectors"]))();keep=(U8*len(g["segs"]))()
        n_ok=0;errors=[];checks=0
        for row in report["rows"]:
            x,y,z,a=row["camera"];i=find_leaf(g,x,y)
            _,mask,ref=cell(i);stats={"runtime_bsp_tests":0};expected=list(walk(ref,x,y,stats))
            t=U32();n=fn(b,len(b),i,x,y,planes,len(g["nodes"]),leaves,len(leaves),keep,C.byref(t))
            ok=n==len(expected) and list(leaves[:max(n,0)])==expected and {k for k,v in enumerate(keep) if v}==mask and t.value==stats["runtime_bsp_tests"]
            n_ok+=ok;checks+=1
            if not ok:errors.append({"camera":[x,y,a],"return":n})
        # Invalid magic and truncated binary must be rejected.
        t=U32();bad=cbuf(b"BAD!"+blob[4:])
        assert fn(bad,len(bad),0,0,0,planes,len(g["nodes"]),leaves,len(leaves),keep,C.byref(t))<0
        assert fn(b,len(b)-1,0,0,0,planes,len(g["nodes"]),leaves,len(leaves),keep,C.byref(t))<0
        result[mode]={"checks":checks,"pass":n_ok,"errors":errors,"bytes":len(blob)}
    return result
def presentation(lib):
    fn=lib.fr_tiles;fn.argtypes=[C.POINTER(U8),C.POINTER(U8),C.c_size_t];fn.restype=C.c_size_t
    rng=random.Random(1993);out=(U8*23040)();passed=0
    for i in range(32):
        src=bytes(rng.randrange(256) for _ in range(11520)) if i else bytes((x//144+x%144)%256 for x in range(11520))
        b=cbuf(src);assert fn(b,out,len(out))==23040
        # Decode tiles back into independent linear pixel matrix, both nibbles.
        linear=bytearray(320*144)
        for y in range(144):
            for x in range(320):
                v=out[((y//8)*40+x//8)*32+(y%8)*4+(x%8)//2]
                linear[y*320+x]=(v>>4) if x%2==0 else v&15
        expected=bytearray()
        for y in range(144):
            for x in range(160):
                v=src[(x//2)*144+(x&1)+2*(y//2)];expected.extend((v>>4,v&15))
        assert linear==expected;passed+=1
    assert fn(b,out,len(out)-1)==0
    return {"frames":passed,"tile_bytes":23040,"tiles":720,"pixel_width":320,"pixel_height":144,"alpha2_dma_order_validated":False}
def assets(lib,wad):
    r=Resources(wad);fn=lib.fr_expand_texture;fn.argtypes=[C.POINTER(U8),C.c_size_t,C.POINTER(U8),C.c_size_t];fn.restype=C.c_size_t
    dest=(U8*24576)();original=packed=passed=0;unique=set()
    for k in sorted(r.defs):
        b,o=r.packed_texture(k);tile=b[o:o+8192]
        assert b==tile*3 and all(v>>4==(v&15) for v in tile)
        data=bytes((tile[i]&240)|(tile[i+1]&15) for i in range(0,8192,2))
        p=cbuf(data);assert fn(p,len(p),dest,len(dest))==len(b) and bytes(dest)==b
        original+=len(b);packed+=len(data);unique.add(hashlib.sha256(data).digest());passed+=1
    # Sprite padding removed by trimming to occupied span source range,
    # preserving logical column origin and transparent gaps.
    sprite_original=sprite_trimmed=0;spans=0;roundtrip=0
    for k in sorted(r.sprites):
        s=r.sprite(k);src=s["pixels"];rebuilt=bytearray(len(src));saved=0
        for i,(first,count) in enumerate(s["columns"]):
            lo=512;hi=0
            for off,a,b in s["spans"][first:first+count]:
                lo=min(lo,off+a//64-i*512);hi=max(hi,off+b//64-i*512);spans+=1
            if count:
                assert 0<=lo<hi<=512
                data=src[i*512+lo:i*512+hi];rebuilt[i*512+lo:i*512+hi]=data
                saved+=len(data)+4
            else:saved+=4
        assert bytes(rebuilt)==src;roundtrip+=1;sprite_original+=len(src);sprite_trimmed+=saved
    return {"textures":passed,"texture_original_bytes":original,"texture_packed_bytes":packed,"texture_dedup_bytes":len(unique)*4096,"sprites":roundtrip,"sprite_spans":spans,"sprite_original_bytes":sprite_original,"sprite_trimmed_bytes":sprite_trimmed,"texture_scratch_bytes":24576,"target_cache_not_integrated":True}
def scaler(rom):
    # Numeric samples only. Discover shape of per-bucket sequences and test
    # independent rational formulas. No extracted tables are emitted.
    def s16(p):return int.from_bytes(rom[p:p+2],"big",signed=True)
    def u32(p):return int.from_bytes(rom[p:p+4],"big")
    seq=[]
    for i in range(2048):
        p=0x21b1c+u32(0x6d4ae+4*i)
        assert 0<=p<=len(rom)-864
        seq.append([s16(p+12*y+10) for y in range(72)])
    groups=collections.Counter(tuple(s) for s in seq)
    # Fit reciprocal sampling from end-to-end slope; report exact coverage
    # instead of assuming a formula is right. Infer per-row linear fixed step.
    # Candidate parameters span common fixed-point conventions.
    candidates=[]
    for numerator in (64,128,256,512,1024,2048,4096,8192,16384):
        for bias in (0,.5,1):
            for center in (35,35.5,36,36.5):
                for mode in ("floor","trunc","nearest"):
                    for offset in (-1,0,1):
                        match=0;total=0
                        for i in range(1,2048,23):
                            d=max(1,i+bias)
                            for y in (0,1,17,35,36,54,71):
                                v=(y-center)*numerator/d
                                pred=(math.floor(v) if mode=="floor" else int(v) if mode=="trunc" else round(v))+offset
                                match+=pred==seq[i][y];total+=1
                        candidates.append((match,total,numerator,bias,center,mode,offset))
    top=sorted(candidates,reverse=True)[:8];best=None
    for _,_,num,bias,center,mode,offset in top:
        match=0
        for i,s in enumerate(seq):
            for y,actual in enumerate(s):
                v=(y-center)*num/max(1,i+bias)
                pred=(math.floor(v) if mode=="floor" else int(v) if mode=="trunc" else round(v))+offset
                match+=pred==actual
        candidate={"matches":match,"numerator":num,"bias":bias,"center":center,"rounding":mode,"offset":offset}
        if best is None or match>best["matches"]:best=candidate
    return {"buckets":2048,"distinct_rows":len(groups),"samples":2048*72,"best_formula":best,"exact":best["matches"]==2048*72,"representative_numeric_samples":[{"bucket":i,"first":seq[i][0],"middle":seq[i][36],"last":seq[i][-1]} for i in (0,1,2,4,8,16,32,64,128,256,512,1024,2047)]}
def main():
    p=argparse.ArgumentParser();p.add_argument("component",choices=["visibility","presentation","assets","scaler"]);p.add_argument("root",type=P);p.add_argument("lib",type=P);p.add_argument("out",type=P);p.add_argument("--rom",type=P);a=p.parse_args()
    lib=load_native(a.lib);wad=None
    if a.component in ("visibility","assets"):
        files=sorted(f for f in a.root.rglob("*") if f.is_file() and f.name.lower()=="doom1.wad");assert files,"doom1.wad missing";wad=WAD(files[0])
    if a.component=="visibility":r=visibility(lib,a.root,wad)
    elif a.component=="presentation":r=presentation(lib)
    elif a.component=="assets":r=assets(lib,wad)
    else:
        rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()=="47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267";r=scaler(rom)
    a.out.write_text(json.dumps(r,indent=2));print("TARGET "+a.component+" "+json.dumps(r),flush=True)
    if a.component=="visibility" and any(v["pass"]!=v["checks"] for v in r.values()):sys.exit(2)
if __name__=="__main__":main()
