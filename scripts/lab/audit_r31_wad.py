#!/usr/bin/env python3
"""Offline-only WAD compression opportunity report.

The renderer accesses WAD lumps randomly; this tool does NOT change WAD bytes
and does NOT assume any decompression can be added without CPU/memory cost.
"""
from pathlib import Path
import hashlib,json,struct,sys,zlib
path=Path(sys.argv[1])
out=Path(sys.argv[2])
wad=path.read_bytes()
if wad[:4] not in (b'PWAD',b'IWAD'):raise SystemExit('invalid WAD')
n=struct.unpack_from('>H',wad,4)[0];directory=struct.unpack_from('>I',wad,8)[0]
if directory+n*16>len(wad):raise SystemExit('invalid directory')
rows=[]
for i in range(n):
    at=directory+i*16
    ptr,sz=struct.unpack_from('>IH',wad,at)
    name=wad[at+8:at+16].split(b'\0')[0].decode('latin1')
    if ptr+sz>len(wad):raise SystemExit('corrupt WAD lump: '+name)
    if not sz:continue
    data=wad[ptr:ptr+sz]
    packed=zlib.compress(data,9)
    gain=sz-len(packed)
    rows.append(dict(lump=name,bytes=sz,zlib_bytes=len(packed),
                     theoretical_gain=max(0,gain),file_offset=ptr,
                     sha256=hashlib.sha256(data).hexdigest()[:12]))
rows.sort(key=lambda e:e['theoretical_gain'],reverse=True)
report={'input':str(path),'wad_bytes':len(wad),'lump_count':n,
        'total_lump_bytes':sum(r['bytes'] for r in rows),
        'optimistic_zlib_gain':sum(r['theoretical_gain'] for r in rows),
        'warning':'potential savings are NOT implementable without verified WAD random-access strategy',
        'top_candidates':rows[:80]}
out.write_text(json.dumps(report,indent=2)+'\n')
print(f"WAD {len(wad)} bytes, {n} lumps, optimistic zlib gains {report['optimistic_zlib_gain']} bytes")
for row in rows[:20]:print(row['lump'],row['bytes'],row['theoretical_gain'])
