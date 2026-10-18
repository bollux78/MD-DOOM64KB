#!/usr/bin/env python3
"""R33: benchmark actual R31 Doom DMX samples. Analysis ONLY: no ROM modification.
All lossless codecs decode byte-identically. IMA-ADPCM is measured as a lossy
4-bit proof-of-concept and NOT assumed to be supported by stock XGM2.
Each sound must remain individually retrievable on demand.
"""
import bz2,collections,hashlib,importlib.util,json,lzma,math,struct,zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('r31_sfx',ROOT/'scripts/lab/gen_r31_sfx.py')
r31=importlib.util.module_from_spec(spec);spec.loader.exec_module(r31)
STEP=(7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,
      50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,
      253,279,307,337,371,408,449,494,544,598,658,724,796,876,
      963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,
      2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,
      7132,7845,8630,9493,10442,11487,12635,13899,15289,
      16818,18500,20350,22385,24623,27086,29794,32767)
INDEX=(-1,-1,-1,-1,2,4,6,8,-1,-1,-1,-1,2,4,6,8)

def rle(data):
    result=bytearray();p=0
    while p<len(data):
        n=1
        while n<128 and p+n<len(data) and data[p+n]==data[p]:n+=1
        if n>=3:
            result+=bytes((127+n,data[p]));p+=n;continue
        start=p;p+=1
        while p<len(data) and p-start<128:
            k=1
            while k<3 and p+k<len(data) and data[p+k]==data[p]:k+=1
            if k>=3:break
            p+=1
        result.append(p-start-1);result+=data[start:p]
    return bytes(result)
def unrle(data):
    out=bytearray();p=0
    while p<len(data):
        n=data[p];p+=1
        if n&128:
            count=(n&127)+1;out+=bytes((data[p],))*count;p+=1
        else:
            count=n+1;out+=data[p:p+count];p+=count
    return bytes(out)
def delta(data):
    prev=0;out=bytearray()
    for x in data:out.append((x-prev)&255);prev=x
    return bytes(out)
def undelta(data):
    prev=0;out=bytearray()
    for x in data:prev=(prev+x)&255;out.append(prev)
    return bytes(out)

def ima_adpcm(data):
    """DVI/IMA 4-bit ADPCM mono, 4-byte independent-sound seed header."""
    pred=0;ind=0;result=bytearray();decoded=bytearray()
    for i,samp in enumerate(data):
        val=(samp-256 if samp>127 else samp)<<8
        step=STEP[ind];diff=val-pred;code=0
        if diff<0:code=8;diff=-diff
        if diff>=step:code|=4;diff-=step
        if diff>=step//2:code|=2;diff-=step//2
        if diff>=step//4:code|=1
        change=step>>3
        if code&4:change+=step
        if code&2:change+=step>>1
        if code&1:change+=step>>2
        pred=max(-32768,min(32767,pred-change if code&8 else pred+change))
        ind=max(0,min(88,ind+INDEX[code]))
        dec=max(-128,min(127,(pred+128)>>8))
        decoded.append(dec&255)
        if not i&1:result.append(code)
        else:result[-1]|=code<<4
    # state header: 16-bit initial predictor, 8-bit index + reserved
    return bytes((0,0,0,0))+bytes(result),bytes(decoded)

def main():
    wadraw,lumps=r31.read_wad(ROOT/'scripts/doom1.wad')
    assert hashlib.sha256(wadraw).hexdigest()=='1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771'
    modes=('half','mixed','full')
    summaries={}
    for mode in modes:
        counts=collections.Counter()
        rows=[]
        aggregate={'signal':0,'error':0}
        seen={}
        for name,priority in r31.SFX:
            lump=lumps['DS'+name.upper()]
            rate=r31.FULL_RATE if mode=='full' or (mode=='mixed' and name in r31.HIGH) else r31.HALF_RATE
            pcm,original_rate,original_samples=r31.convert(lump,rate)
            good=max(1,(original_samples*rate+original_rate//2)//original_rate)
            assert len(pcm)%256==0 and len(pcm)>=good
            signal=pcm[:good]
            raw=bytes(pcm)
            packed={
                'zlib1':zlib.compress(raw,1),
                'zlib9':zlib.compress(raw,9),
                'deflate_raw':zlib.compressobj(level=9,wbits=-15),
                'bz2':bz2.compress(raw,9),
                'lzma_xz':lzma.compress(raw,preset=6),
                'rle':rle(raw),
                'delta_zlib':zlib.compress(delta(raw),9),
            }
            zobj=packed['deflate_raw']
            packed['deflate_raw']=zobj.compress(raw)+zobj.flush()
            assert zlib.decompress(packed['zlib1'])==raw
            assert zlib.decompress(packed['zlib9'])==raw
            assert zlib.decompress(packed['deflate_raw'],-15)==raw
            assert bz2.decompress(packed['bz2'])==raw
            assert lzma.decompress(packed['lzma_xz'])==raw
            assert unrle(packed['rle'])==raw
            assert undelta(zlib.decompress(packed['delta_zlib']))==raw
            compressed={k:len(v) for k,v in packed.items()}
            adpcm,decoded=ima_adpcm(signal)
            assert len(decoded)==len(signal) and len(adpcm)==4+(len(signal)+1)//2
            sig=sum(((v-256 if v>=128 else v)**2) for v in signal)
            noise=sum(((a-256 if a>=128 else a)-(b-256 if b>=128 else b))**2
                      for a,b in zip(signal,decoded))
            aggregate['signal']+=sig;aggregate['error']+=noise
            quiet=0
            for v in signal[::-1]:
                if min(v,256-v)<=2:quiet+=1
                else:break
            sha=hashlib.sha256(signal).hexdigest()
            seen.setdefault(sha,[]).append(name)
            counts['pcm_padded']+=len(raw)
            counts['pcm_unpadded']+=good
            counts['adpcm_4bit']+=len(adpcm)
            for k,v in compressed.items():counts[k]+=v
            rows.append(dict(sound=name,rate=rate,source_rate=original_rate,
                             source_samples=original_samples,
                             pcm_samples=good,pcm_aligned_bytes=len(raw),
                             padding_bytes=len(raw)-good,
                             compressed_bytes=compressed,
                             adpcm_bytes=len(adpcm),adpcm_snr_db=(round(10*math.log10(sig/noise),2)
                                             if sig and noise else None),
                             terminal_near_zero_bytes=quiet))
        sumrows=dict(
            count=len(rows),bytes=dict(sorted(counts.items())),
            adpcm_snr_db=round(10*math.log10(aggregate['signal']/aggregate['error']),2),
            duplicate_pcm_sources=[v for v in seen.values() if len(v)>1],
            max_sample=max(rows,key=lambda r:r['pcm_aligned_bytes']),
            largest_samples=sorted(rows,key=lambda r:r['pcm_aligned_bytes'],reverse=True)[:12],
            per_sfx=rows)
        summaries[mode]=sumrows
        print(f'{mode}: PCM {counts["pcm_padded"]} bytes; byte-exact zlib9 {counts["zlib9"]}, '
              f'delta+zlib9 {counts["delta_zlib"]}, raw-deflate {counts["deflate_raw"]}; '
              f'lossy IMA4 {counts["adpcm_4bit"]} (SNR {sumrows["adpcm_snr_db"]}dB)')
        print('largest:',[(row['sound'],row['pcm_aligned_bytes']) for row in sumrows['largest_samples'][:5]])
    report=dict(source_wad_sha256=hashlib.sha256(wadraw).hexdigest(),
                exact_lossless_roundtrips=True,
                adpcm_warning='EXPERIMENTAL. Stock XGM2 API is 8-bit PCM only; no ADPCM path implemented.',
                constraints=['Every SFX must decode individually, not a single continuous zlib blob.',
                             'Unpacked PCM is 256-aligned and may require two simultaneous output buffers.',
                             'No gameplay FPS or real audio quality validated here.'],
                modes=summaries)
    output=ROOT/'dist/r33/PCM-ALGORITHMS.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
