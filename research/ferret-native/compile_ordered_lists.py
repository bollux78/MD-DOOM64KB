"""Compile FRV2's per-cell masked BSP traversal into ROM-resident ordered lists.
Independent code; no Dread source, executable or original map data imported.
V1 deliberately preserves *every* candidate and leaf boundary. The only
remaining runtime decisions are genuine conditional BSP order switches.
This isolates the cost of traversing the DAG and testing per-wall masks.
"""
import argparse,collections,functools,json,pathlib,re,struct
P=pathlib.Path
def arr(h,k):
    m=re.search(r"static const \w+ "+k+r"\[\d+\]\s*=\s*\{([^}]*)\}",h)
    assert m,k
    return [int(x) for x in m[1].split(",") if x.strip()]
def emit(f,t,k,a):
    f.write(f"static const {t} {k}[{len(a)}] = {{\n")
    for i in range(0,len(a),24):f.write(",".join(map(str,a[i:i+24]))+",\n")
    f.write("};\n")
def compile_scene(h):
    blob=bytes(arr(h,"sc_frv"));leaves=arr(h,"sc_leaves")
    magic,nc,ns,nm,nn,mb=struct.unpack_from(">4sHHHHI",blob)
    assert magic==b"FRV2" and nc*2==len(leaves) and ns<32768
    mo=16+12*nc;no=mo+mb;stride=(ns+7)//8
    assert len(blob)==no+8*nn and mb==nm*stride
    nodes=[struct.unpack_from(">HHHH",blob,no+8*i) for i in range(nn)]
    words=[];offsets=[];intern={};roots=[]
    stats=collections.Counter()
    def block(seq):
        t=tuple(seq)+(0,)
        if t not in intern:
            assert len(offsets)<65535
            intern[t]=len(offsets);offsets.append(len(words));words.extend(t)
        return intern[t]
    @functools.lru_cache(None)
    def expand(ref,mi):
        if ref==65535:return ()
        if ref&32768:
            leaf=ref&32767;assert leaf<nc
            n,first=leaves[leaf*2:leaf*2+2];assert first+n<=ns
            ids=tuple(j for j in range(first,first+n) if blob[mo+mi*stride+j//8]&(1<<(j%8)))
            return (len(ids)+1,)+ids
        op,plane,a,b=nodes[ref]
        assert op in (1,2)
        aa=expand(a,mi);bb=expand(b,mi)
        if op==1:return aa+bb
        return (65535,plane,block(aa),block(bb))
    def count(ref):
        if ref==65535:return 0,0
        if ref&32768:return 1,0
        op,_,a,b=nodes[ref];la,ca=count(a);lb,cb=count(b)
        return la+lb,ca+cb+(op==2)
    for i in range(nc):
        _,_,_,_,mi,ref=struct.unpack_from(">hhhhHH",blob,16+12*i)
        seq=expand(ref,mi);roots.append(block(seq))
        l,c=count(ref)
        stats["leaf_groups"]+=l;stats["conditional_nodes"]+=c
        stats["fixed_cells"]+=c==0
    result={"cells":nc,"walls":ns,"baseline_frv2_bytes":len(blob),"block_count":len(offsets),
            "stream_words":len(words),"list_bytes":2*len(words)+4*len(offsets)+2*nc,
            "maximum_block_offset":max(offsets),"static_leaf_groups":stats["leaf_groups"],
            "residual_conditional_nodes":stats["conditional_nodes"],"fully_fixed_cells":stats["fixed_cells"],
            "format":"group count+1, wall IDs; FFFF plane blockA blockB; zero end. Exact FRV2 order and leaf boundaries."}
    return roots,offsets,words,result
def main():
    p=argparse.ArgumentParser();p.add_argument("scene",type=P);p.add_argument("output",type=P);p.add_argument("report",type=P);a=p.parse_args()
    roots,offsets,words,r=compile_scene(a.scene.read_text())
    with a.output.open("w") as f:
        f.write("/* Precompiled original FRV2 ordered wall streams. */\n")
        f.write(f"#define SC_LIST_BLOCKS {len(offsets)}\n#define SC_LIST_WORDS {len(words)}\n#define SC_LIST_CELLS {len(roots)}\n")
        emit(f,"uint16_t","sc_list_roots",roots);emit(f,"uint32_t","sc_list_offsets",offsets);emit(f,"uint16_t","sc_list_words",words)
    a.report.write_text(json.dumps(r,indent=2));print("ORDERED LIST "+json.dumps(r),flush=True)
if __name__=="__main__":main()
