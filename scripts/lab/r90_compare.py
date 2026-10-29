#!/usr/bin/env python3
from pathlib import Path
import json,re,hashlib
from r90_inject_flats import NAMES,EXPECTED,replace_arrays
base=Path('dist/ab');a=base/'control';b=base/'c-flats'
x=next(a.glob('*-r59_color_tables.h')).read_text();y=next(b.glob('*-r59_color_tables.h')).read_text()
assert hashlib.sha256(x.encode()).hexdigest()==EXPECTED
payload=json.loads(Path('assets/r90-flat-luts-lf050.json').read_text())
assert replace_arrays(x,payload['arrays'])==y,'Unexpected table changes'
ma=json.loads((a/'MANIFEST.json').read_text())[0];mb=json.loads((b/'MANIFEST.json').read_text())[0]
assert ma['bss_bytes']==mb['bss_bytes'],'BSS changed'
# Capture is observational: timed PLAY can draw different game tics as costs vary.
# Do not call a whole-frame mismatch a wall/sprite regression without a pixel ownership mask.
frames=[]
for d in ('smoke-control','smoke-c-flats'):
 p=base/d/'frames.jsonl';rows=[json.loads(l) for l in p.read_text().splitlines()];frames.append(rows)
match={r['tic']:r for r in frames[0]};shared=[r for r in frames[1] if r['tic'] in match]
report={'table_delta':'exactly eight flat array bodies','cram_walls_sprites_hud_tables':'byte-identical','bss_bytes':ma['bss_bytes'],'matched_capture_tics':len(shared),'identical_frame_hashes':sum(r['sha256']==match[r['tic']]['sha256'] for r in shared),'pixel_ownership_validation':'not automated; CRT/image review required; captures supplied'}
(base/'R90-VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
