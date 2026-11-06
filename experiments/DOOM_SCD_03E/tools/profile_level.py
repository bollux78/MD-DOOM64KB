#!/usr/bin/env python3
"""Measure the 03E resource budget before defining the runtime blob ABI."""
import argparse
import hashlib
from pathlib import Path
import struct

LIMIT = 448 * 1024
GEOMETRY = ("VERTEXES", "LINEDEFS", "SIDEDEFS", "SEGS", "SSECTORS", "NODES", "SECTORS")


def aligned_bytes(lumps):
    return sum((len(data) + 3) & ~3 for data in set(lumps))


def profile(data):
    if data[:4] != b"IWAD":
        raise ValueError("expected the converted big-endian R128 IWAD")
    count, directory = struct.unpack_from(">H2xI", data, 4)
    if directory < 12 or directory + count * 16 > len(data):
        raise ValueError("invalid WAD directory")
    names, lumps = [], []
    for index in range(count):
        offset, size, name = struct.unpack_from(">IH2x8s", data, directory + index * 16)
        if size and (offset < 12 or offset + size > len(data)):
            raise ValueError(f"invalid lump range at index {index}")
        names.append(name.rstrip(b"\0").decode("ascii"))
        lumps.append(data[offset:offset + size])

    def named(name):
        return lumps[names.index(name)]

    sprites = lumps[names.index("S_START") + 1:names.index("S_END")]
    texture_defs = named("TEXTUREP")
    name_defs = named("TEXTURE1")
    texture_count, = struct.unpack_from(">I", name_defs)
    offsets = struct.unpack_from(f">{texture_count}H", texture_defs)
    name_offsets = struct.unpack_from(f">{texture_count}I", name_defs, 4)
    sky = next(i for i, off in enumerate(name_offsets) if name_defs[off:off + 8].rstrip(b"\0") == b"SKY1")
    shared = [named(n) for n in ("TEXTUREP", "TEXHEIGH", "COLORMAP")]

    for number in range(1, 10):
        level = f"E1M{number}"
        first = names.index(level)
        end = names.index(f"E1M{number + 1}") if number < 9 else names.index("TEXTURE1")
        local = dict(zip(names[first + 1:end], lumps[first + 1:end]))
        geometry = [local[n] for n in GEOMETRY if n != "VERTEXES" or n in local]
        sides = local["SIDEDEFS"]
        if len(sides) % 7 or len(local["SECTORS"]) % 12:
            raise ValueError(f"{level} is not in the R128 packed map format")
        textures = {sky}
        for offset in range(0, len(sides), 7):
            textures.update(sides[offset + 3:offset + 6])
        textures.discard(0)
        patches = set()
        for index in textures:
            start = offsets[index]
            for patch in range(texture_defs[start + 7]):
                lump, = struct.unpack_from(">H", texture_defs, start + 12 + 8 * patch)
                patches.add(lump)
        base = shared + geometry + [lumps[i] for i in patches]
        fingerprint = hashlib.sha256(b"".join(geometry)).hexdigest()[:12]
        yield level, aligned_bytes(geometry), aligned_bytes(base), aligned_bytes(base + sprites), fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wad", type=Path)
    args = parser.parse_args()
    data = args.wad.read_bytes()
    print(f"WAD SHA256 {hashlib.sha256(data).hexdigest()}")
    print(f"Budget {LIMIT} bytes. Payload estimates only, excluding runtime allocations.")
    print("map   geometry  static+tables  static+all-sprites  headroom  geometry-sha")
    for level, geometry, static, conservative, fingerprint in profile(data):
        print(f"{level} {geometry:10d} {static:14d} {conservative:19d} {LIMIT - conservative:9d}  {fingerprint}")


if __name__ == "__main__":
    main()
