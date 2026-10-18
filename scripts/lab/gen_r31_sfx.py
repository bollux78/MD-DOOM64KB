#!/usr/bin/env python3
"""R31 PCM laboratory for SGDK XGM2.

Genuine Doom DMX DS* samples are read from a user-provided doom1.wad on the
self-hosted runner. The WAD and PCM header are NOT committed to this repository.
All three rates below refer to fixed XGM2 hardware playback, not arbitrary rates.

modes:
 silent  = no SFX, R30b reference
 half    = all SFX 6650 Hz, XGM2_playPCMEx(halfRate=TRUE)
 mixed   = prominent weapons/pain sounds at 13300 Hz, others 6650 Hz
 full    = all SFX 13300 Hz

A sample is *resampled*, not simply flagged at half rate: this is important
to preserve speed and pitch. Data are 8-bit signed, aligned to 256B.
"""
from pathlib import Path
import argparse,collections,hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'scripts/doom1.wad'
HEADER=ROOT/'src/gen_sfx.h'
FULL_RATE=13300
HALF_RATE=6650
# Matches sounds.h 1..52 index order. Doom priorities lower=more urgent.
SFX=[
 ("pistol",64),("shotgn",64),("sgcock",64),("sawup",64),
 ("sawidl",118),("sawful",64),("sawhit",64),("rlaunc",64),
 ("rxplod",70),("firsht",70),("firxpl",70),("pstart",100),
 ("pstop",100),("doropn",100),("dorcls",100),("stnmov",119),
 ("swtchn",78),("swtchx",78),("plpain",96),("dmpain",96),
 ("popain",96),("slop",78),("itemup",78),("wpnup",78),
 ("oof",96),("telept",32),("posit1",98),("posit2",98),
 ("posit3",98),("bgsit1",98),("bgsit2",98),("sgtsit",98),
 ("brssit",94),("sgtatk",70),("claw",70),("pldeth",32),
 ("pdiehi",32),("podth1",70),("podth2",70),("podth3",70),
 ("bgdth1",70),("bgdth2",70),("sgtdth",70),("brsdth",32),
 ("posact",120),("bgact",120),("dmact",120),("noway",78),
 ("barexp",60),("punch",64),("tink",60),("getpow",60)
]
# Rate prioritization is an experimental listening preference, not an
# assertion that these sources originally have 13.3 kHz bandwidth.
HIGH={"pistol","shotgn","sgcock","sawful","sawhit","rlaunc",
      "rxplod","firsht","firxpl","plpain","pldeth","pdiehi",
      "barexp","telept","sgtatk","punch"}

def read_wad(path):
    b=path.read_bytes()
    if b[:4] not in (b'IWAD',b'PWAD'):
        raise ValueError('Invalid WAD signature')
    count,offset=struct.unpack_from('<II',b,4)
    if not 0<count<10000 or offset+count*16>len(b):
        raise ValueError('Invalid WAD directory')
    result={}
    for i in range(count):
        at=offset+16*i
        fp,sz=struct.unpack_from('<II',b,at)
        if fp+sz>len(b):raise ValueError('Invalid WAD lump range')
        name=b[at+8:at+16].split(b'\0')[0].decode('ascii','replace')
        if name.startswith('DS'):result[name]=b[fp:fp+sz]
    return b,result

def convert(lump,target):
    if len(lump)<8:raise ValueError('DMX lump too short')
    fmt,rate,ns=struct.unpack_from('<HHI',lump)
    if fmt!=3 or not 3000<=rate<=48000 or ns==0 or 8+ns>len(lump):
        raise ValueError(f'Invalid DMX PCM format={fmt} rate={rate} len={ns}')
    pcm=lump[8:8+ns]
    # Avoid removing genuine tails in this first audio experiment: no
    # silence trimming, no lossy amplitude quantization, only rate reduction.
    outlen=max(1,(ns*target+rate//2)//rate)
    result=bytearray(outlen)
    for i in range(outlen):
        # Fixed-point 16.16 linear interpolation to reproduce the source pitch.
        pos=(i*rate<<16)//target
        lo=min(ns-1,pos>>16)
        hi=min(ns-1,lo+1)
        frac=pos&65535
        unsigned=(pcm[lo]*(65536-frac)+pcm[hi]*frac+32768)>>16
        result[i]=(unsigned-128)&255
    result+=b'\0'*((-len(result))%256)
    assert len(result)%256==0 and len(result)>0
    return bytes(result),rate,ns

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=('silent','half','mixed','full'),default='silent')
    p.add_argument('--report',type=Path)
    args=p.parse_args()
    parts=[];size=0;sample_hashes={};rates=collections.Counter()
    source_hash=None
    if args.mode!='silent':
        if not SOURCE.is_file():
            raise SystemExit('R31 genuine SFX unavailable: supply scripts/doom1.wad '
                             'or install it in ~/Projetos/doom-assets/ on the runner')
        raw,lumps=read_wad(SOURCE)
        source_hash=hashlib.sha256(raw).hexdigest()
        for name,priority in SFX:
            lump=lumps.get('DS'+name.upper())
            if lump is None:raise SystemExit('Missing DS'+name.upper()+' in doom1.wad')
            rate=FULL_RATE if args.mode=='full' or (args.mode=='mixed' and name in HIGH) else HALF_RATE
            data,source_rate,source_samples=convert(lump,rate)
            prio=max(0,min(15,(128-priority)//8))
            parts.append((name,data,prio,rate==HALF_RATE,source_rate,source_samples))
            size+=len(data)
            rates[rate]+=1
            sample_hashes[name]=hashlib.sha256(data).hexdigest()
    with HEADER.open('w') as f:
        f.write('/* R31: generated offline from user-provided DMX WAD. */\n')
        f.write('#ifndef __GEN_SFX_H__\n#define __GEN_SFX_H__\n#include <stdint.h>\n')
        f.write('#define GENSFX_PCM_ID_BASE 64\n')
        f.write(f'#define GENSFX_COUNT {len(parts)}\n')
        f.write('typedef struct { const uint8_t *data; uint32_t len; uint8_t prio; uint8_t half_rate; } gensfx_t;\n')
        # zero SFX is an explicitly defined variant, not a fallback to silent
        for name,data,*rest in parts:
            f.write(f'static const uint8_t pcm_{name}[] __attribute__((aligned(256))) = {{\n')
            for i in range(0,len(data),32):
                f.write('  '+','.join(str(x) for x in data[i:i+32])+',\n')
            f.write('};\n')
        f.write(f'static const gensfx_t gensfx[{len(parts)+1}] = {{\n')
        f.write('  { 0, 0, 0, 0 },\n')
        for name,data,prio,half,*rest in parts:
            f.write(f'  {{ pcm_{name}, sizeof(pcm_{name}), {prio}, {int(half)} }},\n')
        f.write('};\n#endif\n')
    report={
        'mode':args.mode,
        'source_sha256':source_hash,
        'count':len(parts),
        'sum_pcm_bytes':size,
        'pcm_rates':dict(sorted(rates.items())),
        'alignment':256,
        'samples':[{'name':name,'bytes':len(data),'rate':HALF_RATE if half else FULL_RATE,
                    'source_rate':source_rate,'source_samples':ns}
                   for name,data,prio,half,source_rate,ns in parts],
    }
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in
                      ('mode','count','sum_pcm_bytes','pcm_rates','source_sha256')},indent=2))
if __name__=='__main__':
    main()
