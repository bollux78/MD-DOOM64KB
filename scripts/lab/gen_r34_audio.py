#!/usr/bin/env python3
"""R34-AUDIO: transform only short Doom PCM samples, leave all others original.
Each compressed sound has a strict 2/4 KiB decoded output bound and is
individually decoded into channel-private 256-aligned buffers before XGM2.

IMA-ADPCM is *lossy*. PackBits-RLE is lossless. Both codecs are verified
offline against the same Python decoder logic that is translated to 68000 C.
"""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,json,math,os,struct
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('r31',ROOT/'scripts/lab/gen_r31_sfx.py')
r31=importlib.util.module_from_spec(spec);spec.loader.exec_module(r31)
STEP=(7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,
      50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,
      253,279,307,337,371,408,449,494,544,598,658,724,796,876,
      963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,
      2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,
      7132,7845,8630,9493,10442,11487,12635,13899,15289,
      16818,18500,20350,22385,24623,27086,29794,32767)
INDEX=(-1,-1,-1,-1,2,4,6,8,-1,-1,-1,-1,2,4,6,8)

def packbits(raw):
    out=bytearray();i=0
    while i<len(raw):
        n=1
        while i+n<len(raw) and n<128 and raw[i+n]==raw[i]:n+=1
        if n>=3:
            out+=bytes((0x80+(n-1),raw[i]));i+=n
        else:
            begin=i;i+=1
            while i<len(raw) and i-begin<128:
                if i+2<len(raw) and raw[i]==raw[i+1]==raw[i+2]:break
                i+=1
            out.append(i-begin-1);out+=raw[begin:i]
    return bytes(out)

def unpackbits(raw,expected):
    out=bytearray();i=0
    while i<len(raw):
        code=raw[i];i+=1;n=(code&127)+1
        if code&128:
            assert i<len(raw)
            out+=bytes((raw[i],))*n;i+=1
        else:
            out+=raw[i:i+n];i+=n
    assert len(out)==expected and i==len(raw)
    return bytes(out)

def adpcm_encode_and_decode(raw):
    # Each short effect starts a new decoder at predictor=0, index=0.
    pred=0;idx=0;encoded=bytearray()
    for n,s in enumerate(raw):
        v=(s-256 if s>=128 else s)<<8
        step=STEP[idx];delta=v-pred;code=0
        if delta<0:code=8;delta=-delta
        if delta>=step:code|=4;delta-=step
        if delta>=step//2:code|=2;delta-=step//2
        if delta>=step//4:code|=1
        d=step>>3
        if code&4:d+=step
        if code&2:d+=step>>1
        if code&1:d+=step>>2
        pred=max(-32768,min(32767,pred-d if code&8 else pred+d))
        idx=max(0,min(88,idx+INDEX[code]))
        if n&1:encoded[-1]|=code<<4
        else:encoded.append(code)
    pred=0;idx=0;decoded=bytearray()
    for n in range(len(raw)):
        code=(encoded[n//2] >> (4*(n&1))) & 15
        step=STEP[idx]
        d=step>>3
        if code&4:d+=step
        if code&2:d+=step>>1
        if code&1:d+=step>>2
        pred=max(-32768,min(32767,pred-d if code&8 else pred+d))
        idx=max(0,min(88,idx+INDEX[code]))
        z=max(-128,min(127,(pred+128)>>8))
        decoded.append(z&255)
    assert len(encoded)==(len(raw)+1)//2
    return bytes(encoded),bytes(decoded)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--codec',choices=('adpcm','rle'),required=True)
    p.add_argument('--buffer',type=int,choices=(2048,4096),required=True)
    p.add_argument('--report',type=Path,required=True)
    args=p.parse_args()
    raw_wad,lumps=r31.read_wad(r31.SOURCE)
    sha=hashlib.sha256(raw_wad).hexdigest()
    assert sha=='1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771'
    parts=[];report=[];rates=collections.Counter()
    total_before=total_after=compressed_count=0
    for name,priority in r31.SFX:
        source=lumps['DS'+name.upper()]
        rate=r31.FULL_RATE if name in r31.HIGH else r31.HALF_RATE
        pcm,source_rate,source_len=r31.convert(source,rate)
        orig=bytes(pcm)
        packed=orig;codec=0;snr=None
        if len(orig)<=args.buffer:
            if args.codec=='rle':
                candidate=packbits(orig)
                assert unpackbits(candidate,len(orig))==orig
                if len(candidate)+16<len(orig):
                    packed=candidate;codec=1;snr=None
            else:
                candidate,decoded=adpcm_encode_and_decode(orig)
                sig=sum(((v-256 if v>127 else v)**2) for v in orig)
                err=sum(((v-256 if v>127 else v)-(w-256 if w>127 else w))**2
                        for v,w in zip(orig,decoded))
                snr=round(10*math.log10(sig/err),2) if sig and err else None
                if len(candidate)+16<len(orig):
                    packed=candidate;codec=2
        if codec:
            compressed_count+=1
        total_before+=len(orig);total_after+=len(packed)
        rates[rate]+=1
        prio=max(0,min(15,(128-priority)//8))
        parts.append((name,packed,len(orig),prio,int(rate==r31.HALF_RATE),codec))
        report.append(dict(name=name,rate=rate,codec=codec,raw=len(orig),
                           packed=len(packed),snr_db=snr))
    f=r31.HEADER.open('w')
    with f:
        f.write('/* Experimental R34-AUDIO. Samples >'+str(args.buffer)+'B remain raw. */\n')
        f.write('#ifndef __GEN_SFX_H__\n#define __GEN_SFX_H__\n#include <stdint.h>\n')
        f.write('#define GENSFX_PCM_ID_BASE 64\n#define GENSFX_COUNT 52\n')
        f.write('typedef struct { const uint8_t *data; uint32_t len; uint8_t prio; uint8_t half_rate; uint8_t codec; uint16_t packed_len; } gensfx_t;\n')
        for name,packed,unpacked,prio,half,codec in parts:
            align='256' if codec==0 else '2'
            f.write(f'static const uint8_t pcm_{name}[] __attribute__((aligned({align}))) = {{\n')
            for i in range(0,len(packed),40):
                f.write('  '+','.join(str(v) for v in packed[i:i+40])+',\n')
            f.write('};\n')
        f.write('static const gensfx_t gensfx[53] = {\n')
        f.write('  { 0, 0, 0, 0, 0, 0 },\n')
        for name,packed,unpacked,prio,half,codec in parts:
            f.write(f'  {{ pcm_{name}, {unpacked}, {prio}, {half}, {codec}, sizeof(pcm_{name}) }},\n')
        f.write('};\n#endif\n')
    args.report.parent.mkdir(parents=True,exist_ok=True)
    info=dict(codec=args.codec,buffer_bytes=args.buffer,count=52,
              compressed_count=compressed_count,raw_pcm_bytes=total_before,
              stored_pcm_bytes=total_after,saved_bytes=total_before-total_after,
              rate_counts=dict(rates),source_sha256=sha,
              verification='all lossless PackBits streams byte exact; all ADPCM streams decoded and SNR calculated',
              decoded_pcm_buffers_bytes=2*args.buffer,
              quality_warning='ADPCM lossy. Must listen on BlastEm/real Mega Drive.',
              channel_warning='R34 experimental codec preempts its XGM2 PCM channel before reusing channel-owned output buffer.',
              samples=report)
    args.report.write_text(json.dumps(info,indent=2)+'\n')
    print('R34 AUDIO',args.codec,'buffer',args.buffer,'compressed',compressed_count,
          'saved',info['saved_bytes'],'raw',total_before,'packed',total_after)
    if not compressed_count:raise SystemExit('No SFX selected: invalid experiment')
if __name__=='__main__':main()
