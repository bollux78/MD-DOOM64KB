#!/usr/bin/env python3
"""R48 Pair-V: host oracle for proposed vertical 4x4 decomposition.

This checks the VDP A/B compositing geometry only; it does NOT mean Pair-V
is implemented in a ROM or validated for timing, Window and native art.
"""
import argparse
import random

W, H = 76, 44
PITCH, MAP_COLUMNS, MAP_ROWS = 76, 38, 22
PAIR_BASE = 256
SCREEN_W = 320

def encode_pair_v(samples):
    assert len(samples) == W * H
    buf = bytearray(PITCH * H)
    for y in range(H):
        for x in range(W):
            r = 2 * (y >> 1) + (x & 1)
            at = r * PITCH + ((x >> 1) << 1)
            buf[at] = 1
            color = samples[y * W + x] & 15
            if y & 1:
                buf[at + 1] = (buf[at + 1] & 0xF0) | color
            else:
                buf[at + 1] = (buf[at + 1] & 0x0F) | (color << 4)
    return buf

def tile_pixel(pair, pixel_x, pixel_y):
    assert 0 <= pixel_x < 8 and 0 <= pixel_y < 8
    if pixel_x >= 4:
        return 0
    return (pair >> 4) if pixel_y < 4 else (pair & 15)

def plane_pixel(buf, plane, x, y):
    # HScroll +4 on Plane B moves that plane right 4 pixels.
    scroll = 4 if plane else 0
    src_x = (x - scroll) % 512
    tile_x = src_x // 8
    tile_y = y // 8
    if tile_x >= MAP_COLUMNS or tile_y >= MAP_ROWS:
        return 0
    at = (2 * tile_y + plane) * PITCH + tile_x * 2
    assert buf[at] == 1
    return tile_pixel(buf[at + 1], src_x & 7, y & 7)

def composite_pixel(buf, x, y):
    b = plane_pixel(buf, 1, x, y)
    return b if b else plane_pixel(buf, 0, x, y)

def verify_frame(samples):
    buf = encode_pair_v(samples)
    assert len(buf) == 3344
    for sy in range(H):
        for sx in range(W):
            expected = samples[sy * W + sx] & 15
            for py in range(sy * 4, sy * 4 + 4):
                for px in range(sx * 4, sx * 4 + 4):
                    got = composite_pixel(buf, px, py)
                    if got != expected:
                        raise AssertionError(
                            f"Pair-V sample x={sx} y={sy} expected={expected}, "
                            f"pixel={px},{py} got={got}"
                        )
    for y in (0, 3, 80, 175):
        for x in range(W * 4, SCREEN_W):
            assert composite_pixel(buf, x, y) == 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=40)
    args = ap.parse_args()
    assert args.frames >= 1
    rng = random.Random(0x48A1)
    for p in range(256):
        for yy in range(8):
            for xx in range(8):
                exp = ((p >> 4) if yy < 4 else (p & 15)) if xx < 4 else 0
                assert tile_pixel(p, xx, yy) == exp
    for frame in range(args.frames):
        pixels = [rng.randrange(16) for _ in range(W * H)]
        if frame % 8 == 0:
            pixels = [(x * 3 + y // 2 + frame) & 15
                      for y in range(H) for x in range(W)]
        if frame % 8 == 1:
            pixels = [(y * 5 + x // 2 + frame) & 15
                      for y in range(H) for x in range(W)]
        verify_frame(pixels)
    print(f"R48 PAIR-V GEOMETRY PASS: 256 tiles + {args.frames} "
          "76x44 frames, exact A/B composite with B HScroll +4")
    print("SCOPE: host geometry only; runtime kernels, WINDOW/native art, "
          "DMA and Mega Drive hardware are not yet tested")

if __name__ == "__main__":
    main()
