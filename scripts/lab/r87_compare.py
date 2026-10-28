#!/usr/bin/env python3
"""Report lossy captures. Pixel differences are expected, AI timing is non-equivalent."""
import json,pathlib,sys
import r70_compare
out=pathlib.Path(sys.argv[1]);specs=sys.argv[2:]
rc=r70_compare.main(out,specs)
assert rc in (0,2)
s=json.loads((out/'summary.json').read_text());assert s['common_tics']>=100,s
s['comparison_contract']='Lossy visual variants; no pixel-equivalence gate. AI also changes game state and RNG: timing is a different workload.'
s['best_pixel_identical']=None
(out/'summary.json').write_text(json.dumps(s,indent=2))
lines=['# R87 — visual simplification experiments','',s['comparison_contract'],'',f"Common tics: {s['common_tics']}.",'','See summary.json for measured same-job timing and frame differences.','AI must not be presented as an equivalent simulation speedup.','Other candidates include static sky; compare them with sky as well as control.']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
print('PASS lossy capture report, at least 100 common tics; expected differences retained')
