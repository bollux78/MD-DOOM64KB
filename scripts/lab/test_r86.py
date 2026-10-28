#!/usr/bin/env python3
"""Arithmetic/grouping check. Actual assembled code is gated by BlastEm pixels."""
from pathlib import Path
import random
from apply_r86 import unroll
s=Path('src/r60_pair_wall.s').read_text()
for k in (2,4):
 a=unroll(s,k)
 assert a.count(' dbra %d2,5b')==1 and a.count(' dbra %d2,3b')==1
r=random.Random(86);trials=0
for count in range(1,45):
 for odd in (0,1):
  for _ in range(256):
   f=r.randrange(65536);step=r.randrange(65536);src=bytes(r.randrange(256) for _ in range(128));lut=bytes(r.randrange(16) for _ in range(256));seed=bytearray(r.randbytes(3500))
   def render(k):
    d=seed.copy();at=1;idx=f>>9;lo=(f<<7)&65535
    def tex():
     nonlocal idx,lo
     c=lut[src[idx]];v=lo+((step<<7)&65535);lo=v&65535;idx=(idx+(step>>9)+(v>>16))&127
     return c
    n=count
    if odd:
     d[at]=(d[at]&240)|tex();at+=152;n-=1
    pairs=n//2
    q,rem=divmod(pairs,k)
    for _ in range(q):
     for i in range(k):d[at+152*i]=(tex()<<4)|tex()
     at+=152*k
    for _ in range(rem):d[at]=(tex()<<4)|tex();at+=152
    if n&1:d[at]=(d[at]&15)|(tex()<<4)
    return d,idx,lo
   ref=render(1)
   assert render(2)==ref and render(4)==ref,(count,odd,f,step)
   trials+=1
print('PASS',trials,'phase/step/length cases, complete buffers and final accumulator')
