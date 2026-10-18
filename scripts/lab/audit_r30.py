#!/usr/bin/env python3
"""R30 build-only audit: compare unchanged XGM2 control to native variants."""
from pathlib import Path
import hashlib,json,sys
dist=Path(sys.argv[1]);names=sys.argv[2:]
out=[]
for name in names:
    filename=dist/('doom-md-r30-'+name+'.bin')
    b=filename.read_bytes()
    flags=(dist/('flags-doom-md-r30-'+name+'.txt')).read_text()
    needs=['-DDOOM_R25_MUSIC','-DDOOM_R29_XGM2','-DDOOM_R29_MULTI',
           '-DDOOM_R27_GROUP_SIDE','-DDOOM_R27_GROUP_LINE']
    if name.startswith('native'):needs.append('-DDOOM_R30_NATIVE')
    if name=='control-play' and '-DDOOM_R30_NATIVE' in flags:
        raise SystemExit('Control was contaminated by R30 native flag')
    missing=[n for n in needs if n not in flags]
    if missing:raise SystemExit(f'Invalid build flags in {name}: {missing}')
    if '-DSFX_SILENT' not in flags:raise SystemExit('SFX unexpectedly modified')
    out.append({'name':name,'bytes':len(b),'within_2mib':len(b)<=2097152,
                'sha256':hashlib.sha256(b).hexdigest(),
                'flags_valid':True,'emulator_status':'NOT_TESTED'})
    print(f'VALID R30 {name}: {len(b)} bytes, <=2MiB: {len(b)<=2097152}')
(dist/'R30-SIZES.json').write_text(json.dumps(out,indent=2)+'\n')
