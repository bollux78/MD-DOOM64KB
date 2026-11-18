#!/usr/bin/env python3
"""Check reciprocal topology and reconstruct cached solid/mixed tile output."""
import ctypes as C,json,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]);lib=C.CDLL(str(Path(sys.argv[2]).resolve()));m=json.loads((root/'src/map.json').read_text())
portals=0
for room,(first,count,*_) in enumerate(m['room_records']):
 assert count>=3
 for e in m['edges'][first:first+count]:
  assert e[:2]!=e[2:4]
  assert max(e[8:11])<=m['report']['textures']
  if e[7]!=65535:
   nf,nc,*_=m['room_records'][e[7]]
   back=[q for q in m['edges'][nf:nf+nc] if q[:4]==e[2:4]+e[:2] and q[7]==room]
   assert len(back)==1,(room,e)
   portals+=1
lib.nd_pack_mixed.argtypes=[C.POINTER(C.c_uint8),C.POINTER(C.c_uint32),C.POINTER(C.c_uint16),C.c_uint16,C.c_uint16]
lib.nd_pack_mixed.restype=C.c_uint16
rng=np.random.default_rng(68000)
for case in range(32):
 frame=rng.integers(0,16,(72,40),dtype=np.uint8)
 if case<16:frame[:]=case
 elif case<24:frame[:,20:]=9
 data=(C.c_uint8*2880).from_buffer_copy(frame.tobytes());tiles=(C.c_uint32*(720*8))();mapping=(C.c_uint16*720)()
 count=lib.nd_pack_mixed(data,tiles,mapping,0,1000)
 for ty in range(20):
  for tx in range(36):
   index=mapping[ty*36+tx]
   if index>=1000:actual=np.full((2,2),index-1000)
   else:
    assert index<count
    words=[tiles[index*8+i] for i in range(8)]
    assert len(set(words[:4]))==1 and len(set(words[4:]))==1
    actual=np.array([[words[0]>>28,(words[0]>>12)&15],[words[4]>>28,(words[4]>>12)&15]]).T
   assert np.array_equal(actual,frame[tx*2:tx*2+2,ty*2:ty*2+2]),(case,tx,ty)
print(json.dumps(dict(reciprocal_directed_portals=portals,packing_frames=32,logical_samples_checked=32*2880,errors=0)))
