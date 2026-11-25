from pathlib import Path
import json,sys
root=Path(sys.argv[1])
for name in ['mechanism-results.json','gameplay-results.json','combat-results.json','episode-nine-maps.json']:
 p=root/name
 if not p.exists():continue
 data=json.loads(p.read_text())
 if not isinstance(data,list):continue
 for row in data:
  if 'pass' in row:assert row['pass'],(name,row)
  if row.get('case')=='lift_B':assert row['changed_targets']>0,(name,row)
  if row.get('case')=='masked_wall':assert row['queued']>0,(name,row)
print('Recorded gameplay assertions passed')
