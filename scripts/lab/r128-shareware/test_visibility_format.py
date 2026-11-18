#!/usr/bin/env python3
"""Independently test hidden entries with direct ray/segment intersections."""
import argparse,json,re,struct,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from convert_r24_episode import read_wad
p=argparse.ArgumentParser();p.add_argument('prepared',type=Path);p.add_argument('--samples',type=int,default=20000)
a=p.parse_args();text=(a.prepared/'src/rvis_data.h').read_text()
def array(name):
 raw=re.search(r'\b'+name+r'\[\]\s*=\s*(\{.*?\});',text,re.S).group(1)
 return json.loads(raw.replace('{','[').replace('}',']'))
segs=array('rvis_segs');bits=np.array(array('rvis_bits'),dtype=np.uint8);cells=array('rvis_cells')
meta=re.search(r'int32_t gx=.*?-\((-?\d+)\).*?int32_t gy=.*?-\((-?\d+)\).*?gx<(\d+) && gy<(\d+).*?\*([0-9]+)u;',text,re.S)
xmin,ymin,nx,ny,stride=map(int,meta.groups())
wad=dict((n,d) for n,d in read_wad((a.prepared/'scripts/doom64.wad').read_bytes(),True) if d)
lines=[struct.unpack_from('>hhhhHhhHHhhhhhBbb',wad['LINEDEFS'],i) for i in range(0,len(wad['LINEDEFS']),32)]
walls=np.array([l[:4] for l in lines if not l[14]&4],dtype=np.float64)
wa=walls[:,:2];wd=walls[:,2:]-wa
rng=np.random.default_rng(68000);checked=0;attempts=0
while checked<a.samples:
 attempts+=1
 if attempts>a.samples*100:raise AssertionError('insufficient hidden entries')
 cell=int(rng.integers(len(cells)));i=int(rng.integers(len(segs)))
 if bits[cells[cell]*stride+(i>>3)] & (1<<(i&7)):continue
 s=np.array([xmin+(cell%nx+float(rng.random()))*128,ymin+(cell//nx+float(rng.random()))*128])
 sa=np.array(segs[i][0]);sb=np.array(segs[i][1]);v=sb-sa
 if v[0]*(s[1]-sa[1])-v[1]*(s[0]-sa[0])>=0:checked+=1;continue
 target=sa+(sb-sa)*rng.random();ray=target-s
 denom=ray[0]*wd[:,1]-ray[1]*wd[:,0]
 delta=wa-s
 with np.errstate(divide='ignore',invalid='ignore'):
  t=(delta[:,0]*wd[:,1]-delta[:,1]*wd[:,0])/denom
  u=(delta[:,0]*ray[1]-delta[:,1]*ray[0])/denom
 blocked=np.any((np.abs(denom)>1e-9)&(t>0)&(t<1)&(u>=0)&(u<=1))
 assert blocked,dict(cell=cell,segment=i,source=s.tolist(),target=target.tolist())
 checked+=1
print(json.dumps(dict(seed=68000,hidden_ray_samples=checked,false_rejections=0)))
