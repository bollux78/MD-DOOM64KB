#!/usr/bin/env python3
"""Validate classic Doom map geometry and emit NEXUS ROM data from a local WAD."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

FORMATS = {
    "THINGS": "<hhhhh",
    "LINEDEFS": "<7H",
    "SIDEDEFS": "<hh8s8s8sH",
    "VERTEXES": "<hh",
    "SEGS": "<6H",
    "SSECTORS": "<HH",
    "NODES": "<12h2H",
    "SECTORS": "<hh8s8shhh",
}


def directory(wad):
    if len(wad) < 12 or wad[:4] not in (b"IWAD", b"PWAD"):
        raise ValueError("invalid WAD header")
    count, offset = struct.unpack_from("<II", wad, 4)
    if offset > len(wad) or count > (len(wad) - offset) // 16:
        raise ValueError("invalid WAD directory")
    entries = []
    for start, size, name in struct.iter_unpack("<II8s", wad[offset:offset + 16 * count]):
        if size and (start > len(wad) or size > len(wad) - start):
            raise ValueError(f"lump out of bounds: {name!r}")
        entries.append((name.rstrip(b"\0").decode("ascii"), wad[start:start + size]))
    return entries


def load_map(entries, name):
    for index in range(len(entries) - 1, -1, -1):
        if entries[index][0] == name:
            break
    else:
        raise ValueError(f"{name} missing")
    lumps = dict(entries[index + 1:index + 1 + len(FORMATS)])
    if lumps.keys() != FORMATS.keys():
        raise ValueError(f"{name} is missing classic map lumps")
    records = {key: list(struct.iter_unpack(fmt, lumps[key])) for key, fmt in FORMATS.items()}
    vertices = records["VERTEXES"]
    sectors = [row[:2] for row in records["SECTORS"]]
    # The Q16 edge accumulator must fit signed 32 bits at the near plane.
    heights = [h for sector in sectors for h in sector]
    if not heights or max(heights) - min(heights) > 1000:
        raise ValueError(f"{name}: sector height range exceeds the renderer's Q16 limit")
    lines = records["LINEDEFS"]
    sides = records["SIDEDEFS"]
    segs = []
    for a, b, _, line_index, direction, _ in records["SEGS"]:
        if max(a, b) >= len(vertices) or line_index >= len(lines) or direction > 1:
            raise ValueError(f"{name}: invalid seg")
        line = lines[line_index]
        side = line[5 + direction]
        other = line[6 - direction] if line[2] & 4 else 0xFFFF
        if side >= len(sides) or (other != 0xFFFF and other >= len(sides)):
            raise ValueError(f"{name}: invalid sidedef")
        front = sides[side][-1]
        back = sides[other][-1] if other != 0xFFFF else 0xFFFF
        if front >= len(sectors) or (back != 0xFFFF and back >= len(sectors)):
            raise ValueError(f"{name}: invalid sector")
        segs.append((a, b, front, back))

    leaves = [(first, count) for count, first in records["SSECTORS"]]
    nodes = [(*row[:4], row[-2:], (row[4:8], row[8:12])) for row in records["NODES"]]
    if not leaves or len(leaves) > 0x8000 or len(nodes) > 0x8000:
        raise ValueError(f"{name}: invalid BSP size")
    for first, count in leaves:
        if not count or first + count > len(segs):
            raise ValueError(f"{name}: invalid subsector")
    depths = []
    for node in nodes:
        depth = 0
        for child in node[4]:
            if child & 0x8000:
                if child & 0x7FFF >= len(leaves):
                    raise ValueError(f"{name}: invalid BSP leaf")
                depth = max(depth, 1)
            else:
                if child >= len(depths):
                    raise ValueError(f"{name}: invalid BSP child order")
                depth = max(depth, depths[child] + 1)
        depths.append(depth)
    if depths and depths[-1] > 64:
        raise ValueError(f"{name}: BSP too deep for the prototype")

    root = len(nodes) - 1 if nodes else 0x8000
    spawn = next((row[:3] for row in records["THINGS"] if row[3] == 1), None)
    if spawn is None:
        raise ValueError(f"{name}: missing player start")
    return vertices, sectors, segs, leaves, nodes, root, spawn


def camera_at(data, x, y, angle):
    _, sectors, segs, leaves, nodes, child, _ = data
    while not child & 0x8000:
        nx, ny, dx, dy, children, _ = nodes[child]
        child = children[int(dx * (y - ny) > dy * (x - nx))]
    first, _ = leaves[child & 0x7FFF]
    floor, ceiling = sectors[segs[first][2]]
    z = min(floor + 41, ceiling - 1)
    return x, y, z, round(256 * math.cos(angle)), round(256 * math.sin(angle))


def cameras(data):
    vertices, sectors, segs, _, _, _, (x, y, angle) = data
    radians = math.radians(angle)
    result = [camera_at(data, x, y, radians)]
    candidates = []
    for a, b, front, back in segs:
        if back == 0xFFFF or sectors[front] == sectors[back]:
            continue
        af, ac = sectors[front]
        bf, bc = sectors[back]
        if min(ac, bc) - max(af, bf) < 56:
            continue
        ax, ay = vertices[a]
        bx, by = vertices[b]
        if math.hypot(bx - ax, by - ay) >= 48:
            mx, my = (ax + bx) / 2, (ay + by) / 2
            candidates.append(((mx - x) ** 2 + (my - y) ** 2, mx, my, bx - ax, by - ay))
    if candidates:
        _, mx, my, dx, dy = min(candidates)
        angle = math.atan2(dx, -dy)
        cosine, sine = math.cos(angle), math.sin(angle)
        for distance in (40, 32, 24, 16, 8, 4, -4, -8, -16, -24, -32, -40):
            result.append(camera_at(data, round(mx - distance * cosine),
                                    round(my - distance * sine), angle))
    return result


def initializer(value):
    if isinstance(value, (list, tuple)):
        return "{" + ", ".join(map(initializer, value)) + "}"
    return str(value)


def emit(path, data, map_name):
    vertices, sectors, segs, leaves, nodes, root, _ = data
    arrays = (
        ("NxVertex", "vertices", vertices),
        ("NxSector", "sectors", sectors),
        ("NxSeg", "segs", segs),
        ("NxLeaf", "leaves", leaves),
        ("NxNode", "nodes",
         [(y * dx - x * dy, dx, dy, children, bounds)
          for x, y, dx, dy, children, bounds in nodes]
         or [(0, 0, 0, (0, 0), ((0, 0, 0, 0), (0, 0, 0, 0)))]),
        ("NxCamera", "nexus_cameras", cameras(data)),
    )
    result = ['/* Generated by import_wad.py. */', '#include "nexus.h"']
    for ctype, name, rows in arrays:
        storage = "" if name == "nexus_cameras" else "static "
        result.extend([f"{storage}const {ctype} {name}[] = {{",
                       *(f"    {initializer(row)}," for row in rows), "};"])
    result.extend([
        f"const NxMap nexus_map = {{vertices, sectors, segs, leaves, nodes, {root}}};",
        f'const char nexus_map_name[] = "{map_name}";',
        f"const unsigned int nexus_camera_count = {len(cameras(data))};",
    ])
    path.write_text("\n".join(result) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wad", type=Path)
    parser.add_argument("--maps", nargs="+", default=["E1M1", "E1M2", "E1M9"])
    parser.add_argument("--emit", type=Path, help="write C data for the first map")
    parser.add_argument("--textures", type=Path, help="emit wall materials for the first map")
    parser.add_argument("--line-data", type=Path)
    parser.add_argument("--line-kind", choices=("lines", "wire"), default="lines")
    args = parser.parse_args()
    try:
        wad = args.wad.read_bytes()
        entries = directory(wad)
        maps = {name: load_map(entries, name) for name in args.maps}
        report = {"sha256": hashlib.sha256(wad).hexdigest(), "maps": {}}
        for name, data in maps.items():
            vertices, sectors, segs, leaves, nodes, _, _ = data
            xs, ys = zip(*vertices)
            report["maps"][name] = {
                "vertices": len(vertices), "sectors": len(sectors), "segs": len(segs),
                "leaves": len(leaves), "nodes": len(nodes),
                "bounds": [min(xs), min(ys), max(xs), max(ys)], "poses": cameras(data),
            }
        if args.emit:
            emit(args.emit, maps[args.maps[0]], args.maps[0])
        if args.textures:
            import textures
            textures.emit(entries, args.maps[0], args.textures)
        if args.line_data:
            import line_test
            line_test.emit(args.line_data, entries, args.maps[0], maps[args.maps[0]], args.line_kind)
    except (OSError, ValueError, KeyError, struct.error) as error:
        parser.exit(1, f"NEXUS import: {error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
