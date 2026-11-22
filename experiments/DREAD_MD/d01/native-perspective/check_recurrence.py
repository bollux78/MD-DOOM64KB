#!/usr/bin/env python3
"""Check rational interpolation against integer division, including decreasing U/depth.
This validates the recurrence, not the complete renderer or equivalence to Ferret.
"""
import random
rng=random.Random(0x68000)
count=0
for _ in range(10000):
    n=rng.randint(1,160)
    d=rng.randint(512,1048576)
    dd=rng.randint(-max(0,(d-512)//n),max(0,(1048576-d)//n))
    a=rng.randint(0,1023)*d
    da=rng.randint(-a//n,max(0,(2047*(d+dd*n)-a)//n))
    # Keep the full interval within the converter's supported unsigned numerator.
    if not (0<=a+da*n<2**31 and 0<=a<2**31):continue
    u=a//d;r=a-u*d;delta=da-u*dd
    for x in range(n):
        while r<0:u-=1;r+=d;delta+=dd
        while r>=d:u+=1;r-=d;delta-=dd
        assert u==(a+da*x)//d
        assert r==(a+da*x)%d
        assert -(2**31)<=r+delta<2**31
        count+=1;d+=dd;r+=delta
print(f'{count} exact quotient/remainder comparisons passed')
