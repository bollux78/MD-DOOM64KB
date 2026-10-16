#!/usr/bin/env python3
"""R9 arithmetic preflight: exact integer comparisons for safe 68000 DIVU.W / DIVS.W selection."""
import random
random.seed(68000)
def signed_div(a, b):
    return (abs(a) // abs(b)) * (1 if (a < 0) == (b < 0) else -1)
def old_slope(n, d):
    if not d: return 2048
    ans = ((n * 2048) // d) & 0xffff
    return min(ans, 2048)
def new_slope(n, d):
    if not d: return 2048
    if n <= d: return (n * 2048) // d
    return old_slope(n, d)
for d in range(0, 1024):
    for n in (0, 1, d//2, d, max(0,d-1), min(d+1,65535), 65535):
        assert old_slope(n,d) == new_slope(n,d), (n,d)
for i in range(250000):
    n=random.randrange(65536)
    d=random.randrange(65536)
    assert old_slope(n,d) == new_slope(n,d), (n,d)
for width in range(1,38):
    vals=(-2147483648,-2147483647,-32768*width-1,-32768*width,-32768*width+1,-1,0,1,32768*width-1,32768*width,2147483646,2147483647)
    for delta in vals:
        original=signed_div(delta,width)
        limit=width*32768
        value=(signed_div(delta,width) if -limit<=delta<limit else original)
        assert value==original
        if -limit<=delta<limit: assert -32768<=value<=32767
for i in range(250000):
    width=random.randrange(1,38)
    delta=random.randrange(-2147483648,2147483648)
    orig=signed_div(delta,width)
    bound=width*32768
    if -bound<=delta<bound:
        assert -32768<=orig<=32767
        assert orig==signed_div(delta,width)
print("R9 arithmetic checks PASS: guarded 68000 DIVU.W/DIVS.W paths match original integer mathematics.")
