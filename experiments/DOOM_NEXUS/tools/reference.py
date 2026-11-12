#!/usr/bin/env python3
"""Compare NEXUS frames with independent floating-point ray intersections."""
import argparse
import json
from pathlib import Path

from import_wad import cameras, directory, load_map

WIDTH, HEIGHT, FOCAL, NEAR = 128, 96, 64, 2


def reference(data, camera):
    vertices, sectors, segs, *_ = data
    x, y, eye, cosine, sine = camera
    points = [(((vx - x) * sine - (vy - y) * cosine) / 256,
               ((vx - x) * cosine + (vy - y) * sine) / 256)
              for vx, vy in vertices]
    image = bytearray([7]) * (WIDTH * HEIGHT)
    for column in range(WIDTH):
        slope = (column + 0.5 - WIDTH / 2) / FOCAL
        hits = []
        for a, b, front, back in segs:
            ax, az = points[a]
            bx, bz = points[b]
            delta = (bx - ax) - slope * (bz - az)
            if delta <= 0:
                continue
            along = (slope * az - ax) / delta
            if not 0 <= along < 1:
                continue
            depth = az + along * (bz - az)
            if depth >= NEAR:
                hits.append((depth, a, b, front, back))

        hits.sort()
        for row in range(HEIGHT):
            for depth, a, b, front, back in hits:
                z = eye + (HEIGHT / 2 - row - 0.5) * depth / FOCAL
                floor, ceiling = sectors[front]
                if z > ceiling:
                    color = 1
                elif z <= floor:
                    color = 2
                elif back == 0xFFFF or max(floor, sectors[back][0]) >= min(ceiling, sectors[back][1]):
                    color = 5 + (vertices[a][0] == vertices[b][0])
                elif z > sectors[back][1]:
                    color = 3
                elif z <= sectors[back][0]:
                    color = 4
                else:
                    continue
                image[row * WIDTH + column] = color
                break
    return image


def near_edge(image, index):
    y, x = divmod(index, WIDTH)
    color = image[index]
    return any(image[ny * WIDTH + nx] != color
               for ny in range(max(0, y - 1), min(HEIGHT, y + 2))
               for nx in range(max(0, x - 1), min(WIDTH, x + 2)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wad", type=Path)
    parser.add_argument("frames", type=Path)
    parser.add_argument("--map", default="E1M1")
    parser.add_argument("--2x2", dest="double", action="store_true")
    args = parser.parse_args()
    global WIDTH, HEIGHT, FOCAL
    if args.double:
        WIDTH, HEIGHT, FOCAL = 80, 60, 40
    data = load_map(directory(args.wad.read_bytes()), args.map)
    raw = args.frames.read_bytes()
    poses = cameras(data)
    frame_size = WIDTH * HEIGHT
    if len(raw) != len(poses) * frame_size:
        parser.error("frame count differs from the WAD pose list")

    report = []
    for i, camera in enumerate(poses):
        actual = raw[i * frame_size:(i + 1) * frame_size]
        expected = reference(data, camera)
        mismatch = [p for p, (a, b) in enumerate(zip(actual, expected)) if a != b]
        report.append({
            "pose": i,
            "different_pixels": len(mismatch),
            "different_away_from_reference_edge": sum(not near_edge(expected, p) for p in mismatch),
            "uncovered_pixels": actual.count(7),
            "reference_uncovered_pixels": expected.count(7),
        })
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
