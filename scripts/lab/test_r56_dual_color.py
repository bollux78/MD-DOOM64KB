#!/usr/bin/env python3
"""Pure-Python R56 production-table oracle (no compiler or numpy required)."""
import pathlib,re,struct,sys

p=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else "src/r56_tables.h")
s=p.read_text()
assert "#define R56_ANCHORS" in s
k=int(re.search(r"#define R56_ANCHORS\s+(\d+)",s).group(1))
assert k in (4,6)

def arr(name,shape):
    m=re.search(r"\b"+re.escape(name)+r"((?:\[\d+\])+)[ \t]*=[ \t]*\{(.*?)\};",s,re.S)
    assert m is not None, name
    got=tuple(int(x) for x in re.findall(r"\[(\d+)\]",m.group(1)))
    assert got==shape,(name,got,shape)
    vals=[int(x) for x in re.findall(r"\d+",m.group(2))]
    expected=1
    for n in shape:expected*=n
    assert len(vals)==expected,(name,len(vals),expected)
    return vals

pal=[arr("r56_pal0",(14,16)),arr("r56_pal1",(14,16))]
pairs=[arr("r56_pairs_even",(16,2)),arr("r56_pairs_odd",(16,2))]
wall=[arr("r56_wall_even",(256,)),arr("r56_wall_odd",(256,))]
comp=[arr("r56_comp_even",(34,256)),arr("r56_comp_odd",(34,256))]
flat=[arr("r56_flat_even",(256,)),arr("r56_flat_odd",(256,))]
assert flat[0]==flat[1] and all(1<=x<=k for x in flat[0])
for pidx in range(2):
    assert all(pal[pidx][shade*16]==0 for shade in range(14))
    assert all((w & ~0x0EEE)==0 for w in pal[pidx])
    assert pairs[pidx][:2]==[0,0]
    for code in range(1,16):
        a,b=pairs[pidx][2*code:2*code+2]
        assert 1<=a<=15 and 1<=b<=15,(pidx,code,a,b)
        if code<=k:assert a==b==code,(pidx,code)
    assert all(1<=x<=15 for x in wall[pidx])
    for code in range(16):
        a,b=pairs[pidx][2*code:2*code+2]
        row=((a<<28)|(b<<24)|(a<<20)|(b<<16)) if code else 0
        assert row&0xFFFF==0
        assert [(row>>shift)&15 for shift in (28,24,20,16)]==([a,b,a,b] if code else [0,0,0,0])
for shade in range(14):
    for code in range(1,k+1):
        assert pal[0][shade*16+code]==pal[1][shade*16+code],(shade,code)

wad=pathlib.Path("scripts/doom64.wad").read_bytes()
assert wad[:4]==b"IWAD"
n=struct.unpack_from(">h",wad,4)[0]
ofs=struct.unpack_from(">I",wad,8)[0]
cm=None
for i in range(n):
    pos=ofs+16*i
    name=wad[pos+8:pos+16].split(b"\0")[0]
    if name==b"COLORMAP":
        start=struct.unpack_from(">I",wad,pos)[0]
        size=struct.unpack_from(">H",wad,pos+4)[0]
        cm=wad[start:start+size]
        break
assert cm is not None and len(cm)==34*256
for pidx in range(2):
    assert comp[pidx]==[wall[pidx][x] for x in cm],("COLORMAP",pidx)
    for idx,code in enumerate(flat[pidx]):
        a,b=pairs[pidx][2*code:2*code+2]
        assert a==b==code,(pidx,idx,code)
print("R56 oracle PASS:",p.name,"shared flat anchors",k,"512 ABAB/TTTT tiles, 2x34 COLORMAP, 14 palettes")
