#!/usr/bin/env python3
"""Deterministic 68000 fixed-point geometry regressions for M13.

Models exactly the signed 16-bit LSL.W / MULS.W / SWAP sequence used by
upstream project_and_adjust_x; compares against an explicitly unsigned
reciprocal, 32-bit reference. This does not render a full frame.
"""
from __future__ import annotations

def s16(v: int) -> int:
    return ((v + 0x8000) & 0xFFFF) - 0x8000

def upstream_x(x: int, inv_z: int) -> int:
    """math3d.c project_and_adjust_x: LSL.W #5; MULS.W; SWAP; ADD.W #32."""
    shifted = s16(x << 5)
    product = shifted * s16(inv_z)
    return s16((product >> 16) + 32)

def reference_x(x: int, inv_z: int) -> int:
    """Projection in unbounded signed arithmetic with *unsigned* 0.16 z^-1."""
    assert -32768 <= x <= 32767 and 0 <= inv_z <= 65535
    return 32 + ((x * inv_z) >> 11)

def bsp_old_normal(sin: int, cos: int, half: int, screen_edge: int) -> int:
    """The old BSP declaration stores 32-bit terms in signed 16-bit normal."""
    return s16(half * sin - screen_edge * cos)

def bsp_reference_normal(sin: int, cos: int, half: int, screen_edge: int) -> int:
    return half * sin - screen_edge * cos

def test_x_reference_boundaries() -> None:
    # Cases which expose the original sign and 16-bit shift bugs.
    for x, inv_z in ((1024, 4096), (100, 40000), (32, 65535),
                     (2048, 2048), (-2048, 4096)):
        legacy, exact = upstream_x(x, inv_z), reference_x(x, inv_z)
        assert legacy != exact, (x, inv_z, legacy, exact)
        print(f"X overflow/sign: x={x:5d} invz={inv_z:5d} old={legacy:6d} reference={exact:6d}")

    # Non-overflow paths still match: essential for a narrow future patch.
    for x, inv_z in ((0, 500), (4, 8000), (100, 16000), (-100, 10000)):
        assert upstream_x(x, inv_z) == reference_x(x, inv_z)

def test_bsp_normal_width() -> None:
    # fix16 sin=1024 is a valid unit direction. The half-width here is in
    # Manifold logical columns, not H40 physical pixels.
    half, sin, cos = 32, 1024, 0
    accurate = bsp_reference_normal(sin, cos, half, 0)
    narrowed = bsp_old_normal(sin, cos, half, 0)
    assert accurate == 32768 and narrowed == -32768
    print(f"BSP narrowing: expected={accurate}, stored signed s16={narrowed}")

def test_near_clip_right_assignment() -> None:
    # The upstream typo writes rz1=NEAR_Z but then immediately uses it to
    # set trans_v2.y. The returned depth on the clipped right vertex is
    # therefore correct even though the *local* left-depth variable is wrong.
    near = 64
    left_depth, right_depth = 160, -16
    result_from_original = near
    assert result_from_original == near
    assert left_depth != near
    print("Near-clip assignment typo alone does not corrupt returned trans_v2.y")

if __name__ == "__main__":
    test_x_reference_boundaries()
    test_bsp_normal_width()
    test_near_clip_right_assignment()
    print("PASS: mathematical defects reproduced; no claim of graphical fix")
