#!/usr/bin/env python3
"""R33: real-WAD lossless compression comparison and independent block costs.
Numbers refer to offline *size* only. None of these streams is 68000-playable
without integrating the correct decompressor plus its memory/access policy.
"""
from pathlib import Path
import bz2,collections,hashlib,json,lzma,re,struct,zlib

ROOT=Path(__file__).resolve().parents[2]
WAD=ROOT/'scripts/doom64_aligned.wad'
OUTPUT=ROOT/'dist/r33/WAD-ALGORITHMS.json'
GEOMETRY={'THINGS','LINEDEFS','SIDEDEFS','SEGS','SSECTORS',
          'NODES','SECTORS','REJECT','BLOCKMAP'}

def rle(data):
    out=bytearray();p=0
    while p<len(data):
        run=1
        while p+run<len(data) and run<128 and data[p+run]==data[p]:run+=1
        if run>=3:
            out+=bytes([127+run,data[p]]);p+=run
        else:
            start=p;p+=1
            while p<len(data) and p-start<128:
                if p+2<len(data) and data[p]==data[p+1]==data[p+2]:break
                p+=1
            out.append(p-start-1);out+=data[start:p]
    return bytes(out)
def inverse_rle(data):
    out=bytearray();i=0
    while i<len(data):
        ctrl=data[i];i+=1;size=(ctrl&127)+1
        if ctrl&128:out+=bytes([data[i]])*size;i+=1
        else:out+=data[i:i+size];i+=size
    return bytes(out)

def parse(data):
    if data[:4] not in (b'IWAD',b'PWAD'):raise ValueError('not WAD')
    n=struct.unpack_from('>H',data,4)[0];o=struct.unpack_from('>I',data,8)[0]
    assert o+16*n<=len(data)
    rows=[];current=None
    for k in range(n):
        off=o+16*k
        ptr,sz=struct.unpack_from('>IH',data,off)
        name=data[off+8:off+16].split(b'\0')[0].decode('ascii','replace')
        assert ptr+sz<=len(data)
        if re.fullmatch(r'E1M[1-9]',name):current=name
        elif name not in GEOMETRY:current=None
        map_part=bool(current and name in GEOMETRY)
        extra=bool(re.fullmatch(r'S[1-9](?:LINES|OFFS|SUBS|SOUND|RTHING|RMAP|COFF|CIDX|ROFF|RIDX)',name))
        category='map_geometry' if map_part else 'map_metadata' if extra else 'shared_resource'
        if not sz:continue
        rows.append(dict(id=k,name=name,category=category,map=current if map_part else None,
                         offset=ptr,size=sz,data=data[ptr:ptr+sz]))
    return rows

def comp(data,category,name):
    z1=zlib.compress(data,1);z9=zlib.compress(data,9)
    assert zlib.decompress(z1)==data and zlib.decompress(z9)==data
    b=bz2.compress(data,9)
    assert bz2.decompress(b)==data
    r=rle(data)
    assert inverse_rle(r)==data
    result=dict(zlib1=len(z1),zlib9=len(z9),bz2=len(b),rle=len(r))
    if len(data)>=1536 and name in {'LINEDEFS','SEGS','NODES','BLOCKMAP','SIDEDEFS','TEXTURE1'}:
        prev=0;delta=bytearray()
        for x in data:delta.append((x-prev)&255);prev=x
        zd=zlib.compress(delta,9)
        enc=zlib.decompress(zd);p=0;decoded=bytearray()
        for x in enc:p=(p+x)&255;decoded.append(p)
        assert bytes(decoded)==data
        result['delta_zlib9']=len(zd)
    return result

def main():
    b=WAD.read_bytes()
    assert len(b)==1481876, len(b)
    rows=parse(b);seen={};groups=collections.defaultdict(list)
    for row in rows:
        groups[row['category']].append(row)
        k=(row['offset'],row['size'])
        if k not in seen:seen[k]=row
    reps=sorted(seen.values(),key=lambda r:r['size'],reverse=True)
    summary=collections.defaultdict(lambda:collections.Counter())
    out=[]
    for i,row in enumerate(reps):
        data=row['data']
        sizes=comp(data,row['category'],row['name'])
        agg=summary[row['category']]
        agg['raw']+=len(data);agg['count']+=1
        for k,v in sizes.items():agg['comp_'+k]+=v
        # 4KiB independent blocks. Each block can be decoded from ROM into
        # <=4KiB output buffer, but hot data still need safe random reads.
        for sz in (512,1024,2048,4096):
            cb=sum(len(zlib.compress(data[p:p+sz],1)) for p in range(0,len(data),sz))
            agg[f'zlib1_blocks_{sz}']+=cb
            sizes[f'zlib1_blocks_{sz}']=cb
        rowout={k:row[k] for k in ('id','name','category','map','offset','size')}
        rowout['compressed_bytes']=sizes
        rowout['zlib9_savings']=max(0,len(data)-sizes['zlib9'])
        out.append(rowout)
        if i and i%200==0:print('WAD processed unique lumps:',i,'/',len(reps))
    # Expensive optimal compressor only on the 60 biggest candidates.
    xz=[]
    for row in reps[:60]:
        compxz=lzma.compress(row['data'],preset=6)
        assert lzma.decompress(compxz)==row['data']
        xz.append(dict(name=row['name'],size=row['size'],xz_bytes=len(compxz)))
    totals={k:dict(v) for k,v in summary.items()}
    best=sum(max(0,r['size']-min(r['size'],*(r['compressed_bytes'][k] for k in
        ('zlib9','bz2','rle','zlib1')))) for r in out)
    report=dict(wad_sha256=hashlib.sha256(b).hexdigest(),wad_bytes=len(b),
        count=len(rows),unique_lumps=len(reps),lossless_codec_roundtrips=True,
        codecs=('zlib1','zlib9','bz2','rle','delta_zlib9','zlib1_blocks_512/1024/2048/4096'),
        categories=totals,per_object_best_theoretical_saved=best,
        bz2_individual_overhead_warning='Per-lump overhead can make bz2 worse than raw.',
        zlib_blocks_warning='4KiB block compression size includes separate zlib header per block, not index/pointer overhead.',
        xz_only_60_biggest=xz,
        top_savings=sorted(out,key=lambda r:r['zlib9_savings'],reverse=True)[:80],
        all_lumps=[{k:v for k,v in r.items() if k!='offset'} for r in out])
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,indent=2)+'\n')
    print(f"WAD {len(b)} bytes: {len(reps)} unique lump payloads")
    for name,val in totals.items():
        print(name, {k:val[k] for k in ('count','raw','comp_zlib9','comp_bz2',
                                     'comp_rle','zlib1_blocks_4096')})
    print('Only upper bounds: do not claim runnable cartridge savings.')
if __name__=='__main__':main()
