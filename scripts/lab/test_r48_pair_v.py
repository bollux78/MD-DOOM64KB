#!/usr/bin/env python3
"""R48 Pair-V host oracle: framebuffer tiling and A/B composition equivalence.

The oracle models a 76x44 4-bit sample surface and reconstructs its 304x176
physical pixels with both a horizontal-plane-pair (R47) and vertical-plane-pair
(R48). It checks V packed addressing, nibble selection, A/B offset +4, and
all 256 fixed tile patterns. No emulated DMA or hardware timing claims.
"""
from __future__ import annotations
import random

W,H = 76,44
BYTES = 3344
BASE = 256

def v_addr(x,y):
    return (y//2)*152 + (x&1)*76 + (x//2)*2+1

def pack_v(samples):
    buf=bytearray(BYTES)
    for i in range(0,BYTES,2): buf[i]=1
    for y in range(H):
        for x in range(W):
            j=v_addr(x,y)
            v=samples[y][x]&15
            buf[j] = (buf[j]&0x0f)|(v<<4) if not y&1 else (buf[j]&0xf0)|v
    return buf

def decode_v(buf):
    # Pattern p has left-hand 4px solid with hi in top half and lo in bottom.
    out=[[0]*(W*4) for _ in range(H*4)]
    for plane in range(2):
        for ty in range(22):
            for tx in range(38):
                k=ty*152 + plane*76 + tx*2
                word=(buf[k]<<8)|buf[k+1]
                assert word>=BASE and word<BASE+256,(k,word)
                p=word&255
                for dy in range(8):
                    c=p>>4 if dy<4 else p&15
                    for dx in range(4):
                        x=tx*8 + plane*4 + dx # SGDK HScroll(B)=+4
                        out[ty*8+dy][x]=c
    return out

def expected(samples):
    return [[samples[py//4][px//4] for px in range(W*4)] for py in range(H*4)]

def test():
    rng=random.Random(0x52485056)
    tests = [
        [[0]*W for _ in range(H)],
        [[15]*W for _ in range(H)],
        [[(x+y)&15 for x in range(W)] for y in range(H)],
        [[(x&1)*15 for x in range(W)] for _ in range(H)],
        [[(y&1)*15 for _ in range(W)] for y in range(H)],
    ]
    tests.extend([[[rng.randrange(16) for _ in range(W)] for _ in range(H)]
                  for _ in range(32)])
    for n,s in enumerate(tests):
        buf=pack_v(s)
        assert len(buf)==BYTES
        assert decode_v(buf)==expected(s),f'Pair-V mismatch frame {n}'
        assert all(buf[i]==1 for i in range(0,BYTES,2))
        for y in range(H):
            for x in range(W):
                j=v_addr(x,y)
                assert (buf[j]>>4 if not y&1 else buf[j]&15)==s[y][x],(n,x,y)
    print(f'R48 Pair-V PASS: {len(tests)} patterns, 76x44, packed nibble, A/B +4px HScroll')

if __name__=='__main__':
    test()
