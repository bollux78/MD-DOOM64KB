#!/usr/bin/env python3
"""Check the exact 32-bit / 16-bit reciprocal transformation."""
import random

source = 0xffffffff
reduced = source >> 7
for divisor in list(range(1, 100_000)) + [random.Random(0x68000 + i).randrange(1, 0xffffffff) for i in range(10000)]:
    old = (source // divisor) >> 7
    new = reduced // divisor
    assert old == new, (divisor, old, new)
    if 512 <= divisor <= 65535:
        assert new <= 65535
assert reduced // 512 == 65535
print("PASS: exact reciprocal identities, checked across tested positive divisors")
