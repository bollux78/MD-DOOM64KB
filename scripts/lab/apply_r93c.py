#!/usr/bin/env python3
"""R93c compromise on R92 O1/toggle; p=0 only, unchanged runtime."""
from pathlib import Path
import os
mode=os.environ['R93C_CANDIDATE'];assert mode in ('reference','candidate')
def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:80],s.count(a));p.write_text(s.replace(a,b))
patch('scripts/lab/build_r71a12mul_hud.py',"'r92-'","'r93c-'")
patch('scripts/lab/build_r71a12mul_hud.py',"('toggle', 1)",repr((mode,1)))
if mode=='candidate':
 patch('scripts/lab/gen_r79_shadow.py','  palettes.append(words)', '''  # Approved-for-test Claudio compromise; only p=0 in A2/L3.
  if name in ('A2 Full','L3 Detail'):
   assert strength==1
   payload=json.loads((ROOT/'assets/r93c-compromise.json').read_text())
   spec=payload['A2' if name=='A2 Full' else 'L3']
   before=words.copy()
   for bank,slot,old,new in spec['changes']:
    word=lambda c:(c[0]<<1)|(c[1]<<5)|(c[2]<<9)
    assert int(words[bank,0,slot])==word(old),(name,bank,slot)
    words[bank,0,slot]=word(new)
   assert np.array_equal(words[:,0],np.array(spec['words']))
   assert np.array_equal(words[:,1:],before[:,1:]),'p>0 changed'
   assert np.array_equal(words[:,:,0],before[:,:,0]),'transparent slot changed'
  palettes.append(words)''')
print('R93c',mode,'on R92 toggle, SH1, Off default; compromise not visually approved')
