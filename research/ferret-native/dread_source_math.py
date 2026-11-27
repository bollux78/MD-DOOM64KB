"""Source-derived mathematical scaler model, not copied executable code.

Reference (read-only): Dread source drop, d094f08a2faa1ed0d928d6e22404019e447e53a7,
dreadmake/src/dread_codegen.c, Dread_Build_Scalers and Dread_Build_Scaler_One.
Our independent numerical implementation uses the equivalent floor identity
and a fixed-point remainder accumulator. No Alpha2 ROM or extracted tables
are needed to generate the rows. Optional oracle comparisons remain local.
"""
import argparse, json, pathlib, re, struct, hashlib
P=pathlib.Path

def generate(height=72,center=36,stretch=1,limit=2048):
    assert 0<=center<height and limit>=2 and stretch in (0,1)
    rows=[None]*limit
    groups=[]
    lo,carry=1,0
    while lo<limit:
        amount=max(256,lo*256//30+carry)
        count,carry=divmod(amount,256)
        hi=min(limit,lo+count)
        representative=(lo+hi-1)//2
        # floor((256*(y-center)+255)/size), followed by signed
        # right shift, is one exact floor division by size*2**stretch.
        row=tuple((256*(y-center)+255)//(representative<<stretch) for y in range(height))
        rows[lo:hi]=[row]*(hi-lo)
        groups.append((lo,hi,representative))
        lo=hi
    rows[0]=rows[1]
    return rows,groups

def compact(rows):
    unique={}
    indices=[unique.setdefault(r,len(unique)) for r in rows]
    return list(unique),indices

def decode_fsc(path):
    b=path.read_bytes()
    assert b[:4]==b"FSC1"
    n=struct.unpack_from(">H",b,4)[0]
    assert len(b)==6+10*n
    out=[]
    for i in range(n):
        end,step,bias=struct.unpack_from(">Hii",b,6+10*i)
        assert len(out)<=end<2048
        out.extend([tuple((y*step+bias)//65536 for y in range(72))]*(end+1-len(out)))
    assert len(out)==2048
    return out

def table(scene,name):
    m=re.search(r"(static const \w+ "+name+r"\[\d+\]\s*=\s*\{)([^}]*)(\};)",scene)
    assert m,name
    return m,[int(x) for x in m[2].replace("\n","").split(",") if x.strip()]

def replace_table(scene,name,values):
    m,old=table(scene,name)
    assert len(old)==len(values)
    body="\n"+"".join(",".join(map(str,values[i:i+24]))+",\n" for i in range(0,len(values),24))
    return scene[:m.start(2)]+body+scene[m.end(2):],old==values

def compare(rows,oracle):
    assert len(rows)==len(oracle)==2048
    return {"rows_equal":sum(a==b for a,b in zip(rows,oracle)),
            "samples_equal":sum(a==b for r,s in zip(rows,oracle) for a,b in zip(r,s)),
            "samples":2048*72}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("report",type=P)
    p.add_argument("--fsc",type=P,help="optional private numeric oracle")
    p.add_argument("--scene",type=P,help="optional existing private scene header")
    p.add_argument("--output-scene",type=P)
    a=p.parse_args()
    rows,groups=generate()
    unique,idx=compact(rows)
    assert len(groups)==159 and len(unique)==158 and len(idx)==2048
    # Independent direct arithmetic checks for both halves of screen.
    for i,(lo,hi,s) in enumerate(groups):
        for y in range(72):
            h=2*s*rows[lo][y];target=256*(y-36)+255
            assert h<=target<h+2*s
        assert rows[lo:hi]==[rows[lo]]*(hi-lo)
    result={"upstream":"d094f08a2faa1ed0d928d6e22404019e447e53a7",
            "height":72,"center":36,"stretch":1,"groups":len(groups),
            "distinct_rows":len(unique),"indices":len(idx),"samples":2048*72,
            "generation_requires_alpha2":False,"inequality_checks":len(groups)*72,
            "packed_table_bytes":len(unique)*144+len(idx)}
    if a.fsc:
        result["private_numeric_oracle"]=compare(rows,decode_fsc(a.fsc))
        assert result["private_numeric_oracle"]["samples_equal"]==2048*72
    if a.scene:
        assert a.output_scene
        h=a.scene.read_text()
        values=[x for r in unique for x in r]
        h,e1=replace_table(h,"sc_scalers",values)
        h,e2=replace_table(h,"sc_indices",idx)
        result["scene_tables_equal"]=[e1,e2]
        assert e1 and e2
        a.output_scene.write_text(h)
        result["scene_text_equal"]=a.scene.read_bytes()==a.output_scene.read_bytes()
    a.report.write_text(json.dumps(result,indent=2))
    print("DREAD SOURCE MATH "+json.dumps(result),flush=True)

if __name__=="__main__":main()
