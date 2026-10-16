#!/usr/bin/env python3
"""R10 exact 68000 DIVU.W arithmetic preflight; no emulator timing claims."""
import random
DIVIDEND=0xffffffff
# DIVU.W places remainder in upper word, quotient in low word.
for d in range(1,65536):
    first_q, first_r=divmod(0xffff,d)
    second_q, second_r=divmod((first_r<<16)|0xffff,d)
    assert 0 <= first_q <= 65535 and 0 <= second_q <= 65535
    reconstructed=(first_q<<16)|second_q
    assert reconstructed==DIVIDEND//d, (d,reconstructed,DIVIDEND//d)
def fast_dist(dx, divisor):
    if dx>=0 and 0 < divisor<=65535 and (dx>>16)<divisor:
        quotient=dx//divisor
        assert quotient <= 65535
        return quotient
    return abs(dx)//abs(divisor) * (1 if (dx<0)==(divisor<0) else -1)
rng=random.Random(68010)
for i in range(250000):
    dx=rng.randrange(0,0x80000000)
    divisor=rng.randrange(1,131072)
    expected=dx//divisor
    assert fast_dist(dx,divisor)==expected
for dx in (0,1,65535,65536,65537,0x7fffffff):
    for divisor in (1,2,32767,32768,46340,65534,65535,65536,65537):
        assert fast_dist(dx,divisor)==dx//divisor
print("PASS: 65535 exact 2-step reciprocal cases and 250000+ guarded distance divisions")
