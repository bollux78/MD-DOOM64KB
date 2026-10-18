#!/usr/bin/env python3
"""Build-size audit only; ROMs must be tested on BlastEm and hardware."""
import hashlib,json,sys
from pathlib import Path
dist=Path(sys.argv[1]);variants=sys.argv[2:]
data=[]
for name in variants:
    f=dist/('doom-md-r29-'+name+'.bin')
    raw=f.read_bytes()
    item={'name':name,'bytes':len(raw),'fits_2mib':len(raw)<=2097152,
          'sha256':hashlib.sha256(raw).hexdigest(),'status':'COMPILED_UNTESTED'}
    data.append(item)
    print(f"{name}: {len(raw)} bytes; <= 2 MiB: {item['fits_2mib']}")
(dist/'R29-SIZES.json').write_text(json.dumps(data,indent=2)+'\n')
