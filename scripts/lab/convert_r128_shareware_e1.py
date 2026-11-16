#!/usr/bin/env python3
"""Import all nine Episode 1 maps from the pinned Doom 1.9 shareware IWAD."""
import argparse
import hashlib
import json
from pathlib import Path

from convert_r24_episode import SOURCE_SHA, read_wad
from convert_r128_ultimate_e1 import convert_episode_maps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shareware_wad", type=Path)
    parser.add_argument("--base", type=Path, default=Path(__file__).resolve().parents[1] / "doom64.wad")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = args.shareware_wad.read_bytes()
        source_sha256 = hashlib.sha256(data).hexdigest()
        if source_sha256 != SOURCE_SHA:
            raise ValueError("Expected the pinned Doom 1.9 shareware DOOM1.WAD")
        shareware = read_wad(data)
        base = read_wad(args.base.read_bytes(), True)
        wad, maps = convert_episode_maps(shareware, shareware, base)
        args.out.write_bytes(wad)
    except (AssertionError, KeyError, OSError, ValueError) as error:
        parser.exit(1, f"R128 shareware conversion: {error or 'input exceeds R128 map format'}\n")
    print(json.dumps({
        "iwad_sha256": source_sha256,
        "wad_sha256": hashlib.sha256(wad).hexdigest(),
        "wad_bytes": len(wad),
        "maps": maps,
    }, indent=2))


if __name__ == "__main__":
    main()
