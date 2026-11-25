"""Infer compact fixed-point scaler coefficients from numeric oracle samples.

The affine row fit is independent arithmetic. Run boundaries and coefficients
are calibrated against Alpha2; this is NOT an independent derivation of the
original scale selection rule. No executable instructions are copied.
"""
import argparse,collections,hashlib,json,pathlib,struct
P=pathlib.Path
Q=65536
def ceildiv(a,b):return -(-a//b)
def fit(row):
    # For every y: row[y]*Q <= y*step+bias <= (row[y]+1)*Q-1.
    # Eliminate bias by intersecting all pairwise bounds.
    lo,hi=0,1<<30
    for i,a in enumerate(row):
        for j in range(i+1,len(row)):
            d=j-i;b=row[j]
            lo=max(lo,ceildiv((b-a-1)*Q+1,d))
            hi=min(hi,((b-a+1)*Q-1)//d)
    if lo>hi:return None
    for step in range(lo,hi+1):
        bot=max(a*Q-i*step for i,a in enumerate(row))
        top=min((a+1)*Q-1-i*step for i,a in enumerate(row))
        if bot<=top:
            bias=(bot+top)//2
            if all((i*step+bias)//Q==a for i,a in enumerate(row)):return step,bias
    return None
def main():
    p=argparse.ArgumentParser();p.add_argument("rom",type=P);p.add_argument("private",type=P);p.add_argument("summary",type=P);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()=="47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267"
    rows=[]
    for i in range(2048):
        addr=0x21b1c+int.from_bytes(rom[0x6d4ae+4*i:0x6d4b2+4*i],"big")
        rows.append(tuple(struct.unpack_from(">h",rom,addr+12*y+10)[0] for y in range(72)))
    fitted={r:fit(r) for r in set(rows)}
    runs=[]
    for i,r in enumerate(rows):
        if i==0 or r!=rows[i-1]:runs.append([i,i,r])
        else:runs[-1][1]=i
    result={"distinct_rows":len(fitted),"affine_rows":sum(v is not None for v in fitted.values()),
            "buckets":len(rows),"contiguous_runs":len(runs),"samples":len(rows)*72,
            "exact_values":sum(72 for r in rows if fitted[r] is not None),
            "non_affine_rows":sum(v is None for v in fitted.values()),
            "max_run_length":max(b-a+1 for a,b,_ in runs),"calibration_required":True}
    # Output numeric calibration locally only. A run stores end, signed step and bias.
    a.private.mkdir(parents=True,exist_ok=True)
    if all(v is not None for v in fitted.values()):
        data=bytearray(b"FSC1"+struct.pack(">H",len(runs)))
        for start,end,row in runs:data.extend(struct.pack(">Hii",end,*fitted[row]))
        (a.private/"scaler.fsc").write_bytes(data)
        result["coefficient_bytes"]=len(data)
        # Independent decoder + all samples verification.
        regenerated=[]
        for i in range(len(runs)):
            end,step,bias=struct.unpack_from(">Hii",data,6+10*i)
            while len(regenerated)<=end:regenerated.append(tuple((y*step+bias)//Q for y in range(72)))
        assert regenerated==rows
        result["binary_roundtrip"]=True
    else:
        result["binary_roundtrip"]=False
    # Compare simple recurrence with actual run starts: quantify any formula.
    # Not a proof of original bucket generation.
    result["run_length_histogram"]=dict(collections.Counter(b-a+1 for a,b,_ in runs))
    a.summary.write_text(json.dumps(result,indent=2));print("SCALER FIT "+json.dumps(result),flush=True)
if __name__=="__main__":main()
