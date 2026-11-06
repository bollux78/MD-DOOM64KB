#!/usr/bin/env python3
"""Measure the 03E resource budget before defining the runtime blob ABI."""
import argparse
import hashlib
from pathlib import Path
import re
import struct

LIMIT = 448 * 1024
GEOMETRY = ("VERTEXES", "LINEDEFS", "SIDEDEFS", "SEGS", "SSECTORS", "NODES", "SECTORS")


def aligned_bytes(lumps):
    return sum((len(data) + 3) & ~3 for data in set(lumps))


def sprite_families(things, source):
    info = (source / "info.c").read_text()
    state_table = info.split("const state_t states[NUMSTATES] = {", 1)[1].split("\n};", 1)[0]
    states = {
        label: (sprite, next_state)
        for sprite, next_state, label in re.findall(
            r"\{SPR_(\w+),[^{}\n]*,\s*(S_\w+|0)\s*\}\s*,?\s*//\s*(S_\w+)",
            state_table,
        )
    }
    objects = {
        kind: (int(number), set(re.findall(r"\bS_\w+", body)))
        for kind, number, body in re.findall(
            r"\{\s*//\s*(MT_\w+)\s*\n\s*(-?\d+),([^{}]+)\}", info,
        )
    }
    by_number = {number: kind for kind, (number, _) in objects.items() if number > 0}
    types = {row[2] for row in struct.iter_unpack(">hhhBB", things)}
    kinds = {by_number[number] for number in types - {1, 2, 3, 4, 11}}
    # Player weapons can carry over from another level. Include their effects
    # and the pickups dropped by the two hitscan enemies.
    kinds.update(("MT_PLAYER", "MT_PUFF", "MT_BLOOD", "MT_TFOG", "MT_ROCKET"))
    for actor, effect in (("MT_POSSESSED", "MT_CLIP"), ("MT_SHOTGUY", "MT_SHOTGUN"),
                          ("MT_TROOP", "MT_TROOPSHOT"), ("MT_BRUISER", "MT_BRUISERSHOT")):
        if actor in kinds:
            kinds.add(effect)
    roots = set().union(*(objects[kind][1] for kind in kinds))
    weapons = (source / "d_items.c").read_text().split("const weaponinfo_t weaponinfo", 1)[1]
    roots.update(re.findall(r"\bS_\w+", weapons.split("\n};", 1)[0]))
    visited = {"S_NULL", "0"}
    families = set()
    while roots:
        state = roots.pop()
        if state not in visited:
            visited.add(state)
            family, next_state = states[state]
            families.add(family)
            roots.add(next_state)
    return families


def profile(data, source=None):
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

    sprite_start, sprite_end = names.index("S_START") + 1, names.index("S_END")
    sprites = lumps[sprite_start:sprite_end]
    sprite_names = names[sprite_start:sprite_end]
    texture_defs = named("TEXTUREP")
    name_defs = named("TEXTURE1")
    texture_count, = struct.unpack_from(">I", name_defs)
    offsets = struct.unpack_from(f">{texture_count}H", texture_defs)
    name_offsets = struct.unpack_from(f">{texture_count}I", name_defs, 4)
    texture_ids = {name_defs[off:off + 8].rstrip(b"\0").decode("ascii"): i
                   for i, off in enumerate(name_offsets)}
    sky = texture_ids["SKY1"]
    related = []
    if source is not None:
        switches = (source / "p_switch.c").read_text()
        pairs = re.findall(r'\{"(SW1\w+)",\s*"(SW2\w+)"\s*\}', switches)
        if not pairs:
            raise ValueError("no switch pairs found in R128 source")
        related = [{texture_ids[a], texture_ids[b]} for a, b in pairs]
        related.append(set(range(texture_ids["SLADRIP1"], texture_ids["SLADRIP3"] + 1)))
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
        if level == "E1M1":
            for group in related:
                if textures & group:
                    textures.update(group)
        patches = set()
        for index in textures:
            start = offsets[index]
            for patch in range(texture_defs[start + 7]):
                lump, = struct.unpack_from(">H", texture_defs, start + 12 + 8 * patch)
                patches.add(lump)
        base = shared + geometry + [lumps[i] for i in patches]
        fingerprint = hashlib.sha256(b"".join(geometry)).hexdigest()[:12]
        selected = None
        if source is not None and level == "E1M1":
            families = sprite_families(local["THINGS"], source)
            missing = families - {name[:4] for name in sprite_names}
            if missing:
                raise ValueError(f"{level} has sprite families missing from IWAD: {sorted(missing)}")
            payload = [lump for name, lump in zip(sprite_names, sprites) if name[:4] in families]
            selected = sorted(families), len(payload), aligned_bytes(base + payload)
        yield level, aligned_bytes(geometry), aligned_bytes(base), aligned_bytes(base + sprites), fingerprint, selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wad", type=Path)
    parser.add_argument("--source", type=Path, help="R128 src directory for E1M1 sprite selection")
    args = parser.parse_args()
    data = args.wad.read_bytes()
    print(f"WAD SHA256 {hashlib.sha256(data).hexdigest()}")
    print(f"Budget {LIMIT} bytes. Payload estimates only, excluding runtime allocations.")
    print("map   geometry  static+tables  static+all-sprites  headroom  geometry-sha")
    for level, geometry, static, conservative, fingerprint, selected in profile(data, args.source):
        print(f"{level} {geometry:10d} {static:14d} {conservative:19d} {LIMIT - conservative:9d}  {fingerprint}")
        if selected:
            families, count, size = selected
            print(f"{level} selected: {len(families)} families, {count} lumps, "
                  f"{size} bytes total, {LIMIT - size} bytes remaining")
            print(f"{level} sprite families: {' '.join(families)}")
            if size > LIMIT:
                raise SystemExit("E1M1 selected resource estimate exceeds budget")


if __name__ == "__main__":
    main()
