#!/usr/bin/env python3
"""Arithmetic properties of the P2 split accumulator and M1 signed correction.
These are model tests, not execution of the compiled ROM or its GCC output.
"""
import random

def s16(v):
    v &= 65535
    return v-65536 if v&32768 else v

def original(a,b):
    v=(a*b)&0xffffffff
    if v&0x80000000: v-=0x100000000
    return s16(v>>16)

def proposed(a,b):
    return s16(((a*s16(b))>>16)+(a if b&32768 else 0))

edges=[0,1,2,127,255,511,512,1023,16383,16384,32767,32768,32769,65534,65535]
n=0
for a in range(-32768,32768):
    for b in edges:
        assert original(a,b)==proposed(a,b),(a,b)
        n+=1
for b in range(65536):
    for x in edges:
        a=x-32768
        assert original(a,b)==proposed(a,b),(a,b)
        n+=1
print(f"PASS M1: {n} signed/unsigned edge-domain products")
for low in range(512):
    for step in range(512):
        assert ((low<<7)+(step<<7))>>16 == (low+step)>>9
for ip in range(128):
    for si in range(128):
        for carry in (0,1):
            assert ((ip+si+carry)&127)==((((ip<<9)+(si<<9)+(carry<<9))&65535)>>9)
r=random.Random(20261017)
source=[r.randrange(256) for _ in range(128)]
cellmap=[r.randrange(65536) for _ in range(256)]
for case in range(4096):
    frac=r.randrange(65536); step=r.choice([0,1,511,512,32768,65535,r.randrange(65536)])
    count=case%22+1
    ref=[]; f=frac
    for _ in range(count):
        ref.append(cellmap[source[f>>9]]); f=(f+step)&65535
    got=[]; ip=frac>>9; fl=(frac<<7)&65535; si=step>>9; sl=(step<<7)&65535
    for _ in range(count):
        got.append(cellmap[source[ip]])
        carry=(fl+sl)>>16; fl=(fl+sl)&65535; ip=(ip+si+carry)&127
    assert got==ref,case
print("PASS P2: all fractional/integer transitions and 4096 seeded columns")
