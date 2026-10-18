#!/usr/bin/env python3
"""R33 optional true Sonic-family codec comparison, with byte-for-byte roundtrips.

Use ONLY compressors compiled from the pinned public mdcomp source or already
installed executables. Failures/unsupported input are recorded as such; do not
substitute zlib and label it as Kosinski or Nemesis.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,struct,tempfile

ROOT=Path(__file__).resolve().parents[2]
DIST=ROOT/'dist/r33'
exe_names={
    'kosinski':'kosinskicmp',
    'saxman':'saxmancmp',
    'comper':'compercmp',
    'nemesis':'nemesiscmp',
    'enigma':'enigmacmp'}
spec=importlib.util.spec_from_file_location('r31_sfx',ROOT/'scripts/lab/gen_r31_sfx.py')
audio=importlib.util.module_from_spec(spec);spec.loader.exec_module(audio)
spec=importlib.util.spec_from_file_location('r30_art',ROOT/'scripts/lab/gen_r30_native.py')
art=importlib.util.module_from_spec(spec);spec.loader.exec_module(art)
spec=importlib.util.spec_from_file_location('r33_wad',ROOT/'scripts/lab/bench_r33_wad.py')
wad=importlib.util.module_from_spec(spec);spec.loader.exec_module(wad)

def findexe(name):
    root=os.environ.get('DOOM_R33_MDCOMP_DIR')
    if root:
        p=Path(root)/name
        if p.is_file() and os.access(p,os.X_OK):return str(p)
    return shutil.which(name)

def test(exe,raw,codec):
    with tempfile.TemporaryDirectory(prefix='r33-mdcomp-') as d:
        d=Path(d);a=d/'input.raw';b=d/'encoded.bin';c=d/'decoded.raw'
        a.write_bytes(raw)
        if codec in ('nemesis','enigma') and (len(raw)%2):
            return dict(status='not_applicable',reason='odd-length data')
        if codec=='nemesis' and len(raw)%32:
            return dict(status='not_applicable',reason='not 32-byte tile multiple')
        try:
            p=subprocess.run([exe,str(a),str(b)],stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,timeout=25)
            if p.returncode or not b.exists():
                return dict(status='encode_failed',
                            detail=p.stderr.decode('utf-8','replace')[-300:])
            q=subprocess.run([exe,'-x',str(b),str(c)],stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,timeout=20)
            if q.returncode or not c.exists():
                return dict(status='decode_failed',
                            detail=q.stderr.decode('utf-8','replace')[-300:])
            if c.read_bytes()!=raw:
                return dict(status='roundtrip_mismatch',bytes=len(b.read_bytes()),
                            decoded_bytes=c.stat().st_size)
            return dict(status='ok',bytes=b.stat().st_size,
                        sha256=hashlib.sha256(b.read_bytes()).hexdigest()[:12])
        except subprocess.TimeoutExpired:
            return dict(status='timeout')
        except OSError as exc:
            return dict(status='system_error',detail=str(exc)[:140])

def load_tiles_pack(path):
    p=path.read_bytes();i=0;out=bytearray()
    while i<len(p):
        tile,i=art.decode_one(p,i)
        out+=tile
    assert i==len(p)
    return bytes(out)

def main():
    records=[]
    packed=ROOT/'res/r30-title-pack.bin'
    if packed.is_file():
        records.append(('native_title_tiles',load_tiles_pack(packed),'tiles'))
    tilemap=ROOT/'res/r30-title-map.bin'
    if tilemap.is_file():
        records.append(('native_title_tilemap',tilemap.read_bytes(),'tilemap'))
    aligned=wad.WAD.read_bytes()
    candidates=wad.parse(aligned)
    candidates=sorted((e for e in candidates if e['size']>=1536 and
                       e['name'] in ('LINEDEFS','SEGS','NODES','BLOCKMAP','SIDEDEFS')),
                      key=lambda e:e['size'],reverse=True)
    for i,record in enumerate(candidates[:9]):
        records.append((f"geometry_{i}_{record['name']}_{record['map']}",record['data'],'geometry'))
    _,dmx=audio.read_wad(ROOT/'scripts/doom1.wad')
    raw_sounds=[]
    for name,_ in audio.SFX:
        b,_,_=audio.convert(dmx['DS'+name.upper()],audio.HALF_RATE)
        raw_sounds.append((name,b))
    for name,data in sorted(raw_sounds,key=lambda a:len(a[1]),reverse=True)[:6]:
        records.append((f'pcm_half_{name}',data,'audio'))
    available={codec:findexe(name) for codec,name in exe_names.items()}
    print('True Sega compressors installed:',{k:bool(v) for k,v in available.items()})
    report=[]
    for name,data,kind in records:
        codecs={}
        for codec,exe in available.items():
            if not exe:
                codecs[codec]=dict(status='not_installed')
                continue
            if codec=='enigma' and kind!='tilemap':
                codecs[codec]=dict(status='not_applicable',reason='requires tilemap words')
                continue
            if codec=='nemesis' and kind!='tiles':
                codecs[codec]=dict(status='not_applicable',reason='designed for 4bpp tile patterns')
                continue
            codecs[codec]=test(exe,data,codec)
        record=dict(name=name,category=kind,raw_bytes=len(data),codecs=codecs)
        print(name,len(data),
              {k:v.get('bytes') if v['status']=='ok' else v['status']
               for k,v in codecs.items()})
        report.append(record)
    DIST.mkdir(parents=True,exist_ok=True)
    (DIST/'SONIC-FORMATS.json').write_text(json.dumps(dict(
        source='pinned mdcomp revision 72c6df405a75d322c5b3722da46c3abb864d3793',
        every_success_verified_byte_exact=True,
        installed={k:bool(v) for k,v in available.items()},
        warning='Comparative host compression only; no 68000 depackers or decode FPS yet.',
        results=report),indent=2)+'\n')
if __name__=='__main__':main()
