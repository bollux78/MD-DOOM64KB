#!/usr/bin/env python3
"""Build a common, lossless tile dictionary for the HUD, faces and weapon."""
import re
import sys
from pathlib import Path

from pack_episode import array


def main():
    hud, weapon, output = (Path(p) for p in sys.argv[1:])
    unique = []
    index = {}
    weapon_source = weapon.read_text()
    frame_tiles = int(re.search(r"\bweap_tiles = (\d+)", weapon_source)[1])
    out = ["/* Generated tile dictionary. */", f"#define EP_WEAPON_TILES {frame_tiles}"]
    source = hud.read_text() + weapon_source
    for symbol in ("hudw_tiles", "hudw_faces"):   # the weapon stays raw in ROM: frames DMA straight from ROM (no RAM frame buffer)
        body = re.search(r"\b" + symbol + r"(?:\[\d+\])+\s*=\s*\{([^;]+);", source)[1]
        words = [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", body)]
        if not words or len(words) % 8:
            raise ValueError(f"{symbol}: expected complete tiles")
        refs = []
        for pos in range(0, len(words), 8):
            tile = tuple(words[pos:pos+8])
            if tile not in index:
                index[tile] = len(unique)
                unique.append(tile)
            refs.append(index[tile])
        if any(unique[ref] != tuple(words[pos:pos+8]) for pos, ref in zip(range(0, len(words), 8), refs)):
            raise ValueError(f"{symbol}: dictionary round trip failed")
        out.append(array(symbol + "_refs", refs, "uint16_t"))
    words = [f"0x{x:08X}u" for tile in unique for x in tile]
    out.append(array("image_tiles", words, "uint32_t"))
    output.write_text("\n".join(out) + "\n")
    print(f"HUD/weapon dictionary: {len(unique)} unique tiles, {len(words)*4} bytes plus indices")


if __name__ == "__main__":
    main()
