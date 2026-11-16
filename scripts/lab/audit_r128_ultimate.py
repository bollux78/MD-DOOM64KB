#!/usr/bin/env python3
"""Report which Ultimate Doom map data fits the R128 format without rewriting it."""
import argparse
import hashlib
import json
from pathlib import Path

from convert_r24_episode import definitions, map_at, read_wad, recs, texnames

MAPS = tuple(f"E{episode}M{level}" for episode in range(1, 5) for level in range(1, 10))
MAP_LUMPS = {
    "THINGS", "LINEDEFS", "SIDEDEFS", "VERTEXES", "SEGS",
    "SSECTORS", "NODES", "SECTORS", "REJECT", "BLOCKMAP",
}


def map_stats(lumps, known_things, known_textures):
    lines = recs(lumps["LINEDEFS"], "<7H")
    sides = recs(lumps["SIDEDEFS"], "<hh8s8s8sH")
    # R128 keeps independently mutable sides unique and deduplicates the rest.
    mutable = {side for line in lines if line[3] for side in line[5:] if side != 0xffff}
    compact_sides = len(mutable) + len({side for i, side in enumerate(sides) if i not in mutable})
    things = [t for t in recs(lumps["THINGS"], "<5h") if t[3] not in {2, 3, 4, 11} and not t[4] & 16]
    textures = {name.split(b"\0", 1)[0].decode("ascii").upper()
                for side in sides for name in side[2:5]} - {"", "-"}
    sectors = len(recs(lumps["SECTORS"], "<hh8s8s3h"))
    segs = len(recs(lumps["SEGS"], "<6H"))
    compact_bytes = {"THINGS": len(things) * 8, "LINEDEFS": len(lines) * 32,
                     "SIDEDEFS": compact_sides * 7, "SEGS": segs * 18,
                     "SECTORS": sectors * 12, **{name: len(lumps[name])
                     for name in ("SSECTORS", "NODES", "REJECT", "BLOCKMAP")}}
    return {
        "sectors": sectors, "linedefs": len(lines), "segs": segs,
        "source_map_bytes": sum(map(len, lumps.values())),
        "projected_compact_map_bytes": compact_bytes,
        "converter_sector_limit_exceeded": sectors >= 255,
        "converter_linedef_limit_exceeded": len(lines) >= 2048,
        "compact_lumps_over_16_bits": sorted(name for name, size in compact_bytes.items() if size > 65535),
        "required_wall_textures": sorted(textures),
        "missing_wall_textures": sorted(textures - known_textures),
        "unsupported_thing_types": sorted({t[3] for t in things} - known_things),
        "linedef_specials": sorted({line[3] for line in lines} - {0}),
        "specials_outside_signed_byte": sorted({line[3] for line in lines if line[3] >= 128}),
    }


def audit(raw, compact, shareware=None):
    source = read_wad(raw)
    if any(sum(key == name for key, _ in source) != 1 for name in MAPS):
        raise ValueError("Expected one copy of each Ultimate Doom map from E1M1 to E4M9")
    texture_names = set(texnames(dict(read_wad(compact, True))["TEXTURE1"]))
    known_things = {int(d["doomednum"]) for d in definitions()} | {1}
    reference = read_wad(shareware) if shareware is not None else None
    report = {"input_bytes": len(raw), "input_sha256": hashlib.sha256(raw).hexdigest(),
              "map_count": len(MAPS), "maps": {}}
    for name in MAPS:
        lumps = map_at(source, name, original=True)
        if set(lumps) != MAP_LUMPS:
            raise ValueError(f"{name}: unexpected map lump layout")
        row = map_stats(lumps, known_things, texture_names)
        if reference is not None and name.startswith("E1"):
            old = map_at(reference, name, original=True)
            row["changed_lumps_vs_shareware"] = sorted(key for key in lumps if old[key] != lumps[key])
        report["maps"][name] = row
    report["required_wall_texture_count"] = len(set().union(*(m["required_wall_textures"] for m in report["maps"].values())))
    report["missing_wall_texture_count"] = len(set().union(*(m["missing_wall_textures"] for m in report["maps"].values())))
    report["unsupported_thing_type_count"] = len(set().union(*(m["unsupported_thing_types"] for m in report["maps"].values())))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ultimate_wad", type=Path)
    parser.add_argument("--base", type=Path, default=Path(__file__).resolve().parents[1] / "doom64.wad")
    parser.add_argument("--shareware", type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.ultimate_wad.read_bytes(), args.base.read_bytes(),
                       args.shareware.read_bytes() if args.shareware else None)
    except (AssertionError, KeyError, OSError, ValueError) as error:
        parser.exit(1, f"R128 audit: {error or 'invalid WAD format'}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
