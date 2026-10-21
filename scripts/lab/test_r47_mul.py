#!/usr/bin/env python3
"""Mathematical oracle for R47 low-32 exact 68000 multiply decomposition."""
import random
MASK=(1<<32)-1
def s16(x):
    x&=0xffff
    return x-0x10000 if x&0x8000 else x
def s32(x):
    x&=MASK
    return x-(1<<32) if x&0x80000000 else x
def helper(a,b):
    a&=MASK;b=s16(b)
    lo=a&0xffff;hi=s16(a>>16)
    low=(lo*(b&0xffff))&MASK
    if b<0: low=(low-(lo<<16))&MASK
    high=(hi*b)&MASK
    return s32((low+(high<<16))&MASK)
def ref(a,b): return s32((s32(a)*s16(b))&MASK)
edges=[0,1,-1,0x7fffffff,-0x80000000,0x12345678,-0x1234567]
bedges=[0,1,-1,32767,-32768,0x1234,-0x2345]
for a in edges:
    for b in bedges:
        assert helper(a,b)==ref(a,b),(a,b,helper(a,b),ref(a,b))
r=random.Random(0x47B)
for i in range(1000000):
    a=r.getrandbits(32);b=r.getrandbits(16)
    if helper(a,b)!=ref(a,b): raise AssertionError((i,a,b,helper(a,b),ref(a,b)))
print("R47 PASS: 1,000,049 exact 32x16 wraparound multiply cases")
