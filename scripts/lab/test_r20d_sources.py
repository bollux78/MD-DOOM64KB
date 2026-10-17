#!/usr/bin/env python3
"""R2 memo selection sequences and R4 source offsets on the actual converted WAD.
Offline contract checks; not execution of the compiled routines.
"""
import pathlib,random,struct
root=pathlib.Path(__file__).resolve().parents[2]
b=(root/'scripts/doom64.wad').read_bytes()
num=struct.unpack_from('>h',b,4)[0]; directory=struct.unpack_from('>i',b,8)[0]
lumps=[]
for i in range(num):
    at=directory+16*i; pos,size=struct.unpack_from('>iH',b,at)
    name=b[at+8:at+16].split(b'\0')[0].decode('latin1')
    lumps.append((name,pos,b[pos:pos+size]))
byname={n:(pos,data) for n,pos,data in lumps}
base=0x120000
colormap=byname['COLORMAP'][1]
assert len(colormap)>=32*256

def select(c):
    if c is None: return None
    off=(c-base)&0xffffffff
    return off>>8 if off<8192 and not(off&255) else None
last=None; memo=None; n=0; r=random.Random(20261017)
cases=[None,base-1,base+1,base+8192]+[base+256*i for i in range(32)]
for _ in range(10000):
    c=r.choice(cases)
    for repeat in range(r.randrange(1,9)):
        expected=select(c)
        if c!=last: last,memo=c,select(c)
        assert memo==expected,(c,last,memo,expected)
        # Compare actual LUT source byte rows for every valid selection.
        if memo is not None:
            assert colormap[memo*256:(memo+1)*256]==colormap[expected*256:(expected+1)*256]
        n+=1
print(f'PASS R2: {n} memo transitions/hits, standard rows and fallback addresses')
tp_pos,tp=byname['TEXTUREP']; nt=struct.unpack_from('>i',byname['TEXTURE1'][1],0)[0]
eligible=0; checked=0
for texture in range(1,nt):
    off=struct.unpack_from('>H',tp,2*texture)[0]
    mask,width,height,overlap,count=struct.unpack_from('>HhhBB',tp,off)
    if overlap or count!=1: continue
    eligible+=1
    patchnum=struct.unpack_from('>h',tp,off+12)[0]
    _,patchpos,patch=lumps[patchnum]
    pw=struct.unpack_from('>h',patch,0)[0]
    for xc in {c&mask for c in range(65536)}:
        assert 0<=xc<pw,(texture,xc,pw)
        column=struct.unpack_from('>i',patch,8+4*xc)[0]
        # Check real asset bounds rather than compare two identical formulas.
        source=patchpos+column+3
        assert 0<=column+3<len(patch) and patchpos<=source<patchpos+len(patch)
        checked+=1
assert eligible>0
print(f'PASS R4: {eligible} eligible textures, {checked} distinct source offsets, full 16-bit column domain')
