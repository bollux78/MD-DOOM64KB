#!/usr/bin/env python3
"""Classic Doom WAD reader, adapted from the earlier NEXUS import tool."""
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

