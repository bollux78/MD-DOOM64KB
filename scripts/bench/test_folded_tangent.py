#!/usr/bin/env python3
"""Verify index/sign folding for every 12-bit fine angle.

No trigonometric approximation: the folded index selects precisely the
same original half-table value with precisely the same sign.
"""
for ang in range(4096):
    if ang < 1024:
        old = ("part4", 1023 - ang, +1)
    elif ang < 2048:
        old = ("part3", 2047 - ang, +1)
    elif ang < 3072:
        old = ("part3", ang - 2048, -1)
    else:
        old = ("part4", ang - 3072, -1)
    folded = (2047 - ang) if ang < 2048 else (ang - 2048)
    new = (
        "part3" if folded < 1024 else "part4",
        folded if folded < 1024 else folded - 1024,
        +1 if ang < 2048 else -1,
    )
    assert old == new, (ang, old, new)
print("PASS: all 4096 tangent lookups select exactly the same value and sign")
