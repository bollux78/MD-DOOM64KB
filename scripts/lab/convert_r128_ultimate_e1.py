#!/usr/bin/env python3
"""Prepare the authentic Ultimate Doom episode 1 in the R128 map format."""
import argparse
import hashlib
import json
from pathlib import Path

from convert_r24_episode import (SOURCE_SHA, TARGET_ORDER, convert_map, definitions,
                                 flat_colors, map_at, metadata, read_wad, write_wad)


def convert_episode(ultimate, shareware, compact):
    if hashlib.sha256(shareware).hexdigest() != SOURCE_SHA:
        raise ValueError("Expected the R128's original shareware reference for flat colors")
    source = read_wad(ultimate)
    reference = read_wad(shareware)
    base = read_wad(compact, True)
    if not any(name == "E4M9" for name, _ in source):
        raise ValueError("Expected an Ultimate Doom IWAD")

    defs = definitions()
    converted = list(base)
    reports = []
    for level in range(1, 10):
        name = f"E1M{level}"
        original = map_at(source, name, original=True)
        colors, fallback = flat_colors(original, source, reference, base)
        maps, report = convert_map(original, base, colors, name)
        marker = next(i for i, (key, _) in enumerate(converted) if key == name)
        converted[marker + 1:marker + 10] = [(key, maps[key]) for key in TARGET_ORDER]
        groups, statics = metadata(maps, level, defs)
        group_names = {key for key, _ in groups}
        converted = [(key, data) for key, data in converted if key not in group_names]
        converted.extend(groups)
        reports.append({"map": name, "sectors": report["sectors"],
                        "linedefs": report["linedefs"], "things": report["things"],
                        "rom_static_candidates": statics, "flat_color_fallbacks": len(set(fallback))})
    return write_wad(converted), reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ultimate_wad", type=Path)
    parser.add_argument("--shareware", type=Path, required=True)
    parser.add_argument("--base", type=Path, default=Path(__file__).resolve().parents[1] / "doom64.wad")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        wad, maps = convert_episode(args.ultimate_wad.read_bytes(), args.shareware.read_bytes(),
                                    args.base.read_bytes())
        args.out.write_bytes(wad)
    except (AssertionError, KeyError, OSError, ValueError) as error:
        parser.exit(1, f"Ultimate E1 conversion: {error or 'input exceeds R128 map format'}\n")
    print(json.dumps({"wad_bytes": len(wad), "sha256": hashlib.sha256(wad).hexdigest(), "maps": maps}, indent=2))


if __name__ == "__main__":
    main()
