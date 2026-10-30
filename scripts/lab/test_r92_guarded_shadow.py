#!/usr/bin/env python3
"""Host tests of offline constraints and exhaustive joint-table rewrites."""
import numpy as np
from r92_guarded_shadow import fit_row,beige_bad,rewrite_table,de
colors=np.zeros((2,16,3));colors[:]=[80,25,35];colors[:,1]=[50,0,0]
target=np.array([[50,0,0],[50,0,0]])
new,info=fit_row(target,(2,2),colors);assert new==(1,1) and info['beige']
new,info=fit_row(target,(1,1),colors);assert new==(1,1) and not info['suspect']
new,_=fit_row(target,(0,2),colors);assert new==(0,2)
rng=np.random.default_rng(92);changes=0
for _ in range(3000):
 c=rng.uniform([-0.,-60.,-60.],[100.,60.,60.],size=(2,16,3));t=c[[0,1],rng.integers(1,16,size=2)];old=tuple(rng.integers(1,16,size=2))
 new,info=fit_row(t,old,c)
 if new!=old:
  changes+=1;o=c[[0,1],old];n=c[[0,1],new]
  assert np.all(de(n,t)<=de(o,t)+1e-8)
  assert de(n[0],n[1])<=de(o[0],o[1])+1e-8
  assert not np.any(beige_bad(t,n))
  assert np.all(np.abs(n[:,0]-t[:,0])<=np.abs(o[:,0]-t[:,0])+1e-8)
  assert np.all(np.abs(np.linalg.norm(n[:,1:],axis=-1)-np.linalg.norm(t[:,1:],axis=-1))<=np.abs(np.linalg.norm(o[:,1:],axis=-1)-np.linalg.norm(t[:,1:],axis=-1))+1e-8)
 else:
  if not info['suspect']:assert new==old
assert changes>0
keys=np.arange(65536,dtype=np.uint32);state=(keys&1);original=((0x100|((1-state)<<15)|(keys>>8))<<16)|(0x2200|(keys&255))
rows=np.zeros((2,16,16,2),dtype=np.uint8)
for st in (0,1):
 for a in range(16):
  for b in range(16):rows[st,a,b]=[a,b]
assert np.array_equal(rewrite_table(original,rows),original)
rows[:,3,4]=[5,6];out=rewrite_table(original,rows)
for k in range(65536):
 ca,cb=k>>8,k&255;expected=int(original[k])
 for shift in (0,4):
  if ((ca>>shift)&15,(cb>>shift)&15)==(3,4):expected=(expected&~((15<<(16+shift))|(15<<shift)))|(5<<(16+shift))|(6<<shift)
 assert int(out[k])==expected,k
print('PASS targeted beige, unchanged approved rows, transparency guard, 3000 constraint cases and 65536 independent packed-block checks; changes:',changes)
