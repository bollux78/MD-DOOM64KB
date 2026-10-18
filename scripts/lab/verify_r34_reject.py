#!/usr/bin/env python3
"""Check EVERY WAD lump against original, fully decompressing REJECT streams.
This is an offline correctness oracle, not merely a successful ROM build.
"""
import hashlib,json,struct,sys
from pathlib import Path

def parse(path):
    b=Path(path).read_bytes()
    assert b[:4] in (b'IWAD',b'PWAD')
    n=struct.unpack_from('>H',b,4)[0];at=struct.unpack_from('>I',b,8)[0]
    assert at+16*n<=len(b)
    rows=[]
    for i in range(n):
        j=at+16*i;off=struct.unpack_from('>I',b,j)[0]
        sz=struct.unpack_from('>H',b,j+4)[0]
        name=b[j+8:j+16].rstrip(b'\0').decode('ascii','replace')
        assert off+sz<=len(b)
        rows.append((name,b[off:off+sz]))
    return b,rows

def expand(data,blocksize):
    assert data[:4]==b'RJ64'
    original,n=struct.unpack_from('>HH',data,4)
    assert n==(original+blocksize-1)//blocksize
    body=8+(n+1)*2
    offsets=[struct.unpack_from('>H',data,8+j*2)[0] for j in range(n+1)]
    assert offsets[0]==0 and body+offsets[-1]==len(data)
    out=bytearray()
    for j in range(n):
        assert offsets[j]<offsets[j+1]
        start=body+offsets[j];end=body+offsets[j+1]
        part=data[start:end];expected=min(blocksize,original-len(out))
        if part[0]==0:
            piece=part[1:]
        else:
            assert part[0]==1
            tmp=bytearray();i=1
            while i<len(part):
                ctl=part[i];i+=1;count=(ctl&127)+1
                if ctl&128:
                    assert i<len(part)
                    tmp+=bytes((part[i],))*count;i+=1
                else:
                    assert i+count<=len(part)
                    tmp+=part[i:i+count];i+=count
            piece=bytes(tmp)
        assert len(piece)==expected,(j,len(piece),expected)
        out+=piece
    assert len(out)==original
    return bytes(out)

def main():
    source,packed,output=sys.argv[1:4]
    blocksize=int(sys.argv[4]);enable=int(sys.argv[5])
    a,x=parse(source);b,y=parse(packed)
    assert len(x)==len(y)
    pictures={b'TITLEPIC',b'WIMAP0',b'HELP2'}
    pairs=[]
    compressed=0;saved=0;names=[]
    for (key,left),(key2,right) in zip(x,y):
        assert key==key2,key
        if key.encode() in pictures and len(left)==38400:
            assert right==b'',(key,len(right))
            continue
        if enable and key=='REJECT' and right[:4]==b'RJ64':
            inflated=expand(right,blocksize)
            assert inflated==left,('R34 REJECT mismatch',key)
            compressed+=1;saved+=len(left)-len(right)
            pairs.append((len(left),len(right)))
        else:
            assert left==right,(key,len(left),len(right))
    assert compressed>0 if enable else compressed==0
    result=dict(enabled=bool(enable),blocksize=blocksize,
        baseline_wad_bytes=len(a),packed_wad_bytes=len(b),
        saved_bytes_by_reject=saved,compressed_reject_lumps=compressed,
        reject_sizes=pairs,all_non_reject_lumps_exact=True,
        all_reject_lumps_exact=True,
        packed_sha256=hashlib.sha256(b).hexdigest())
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print('R34 WAD verify',json.dumps(result))
if __name__=='__main__':main()
