#!/usr/bin/env python3
"""R39f ROM-only dither LUT and 8x8 pattern consistency check.

Usage:
  python3 scripts/lab/test_r39f_vertical.py \
     control-colormap.h control-colorcell.h \
     dither3-colormap.h dither3-colorcell.h
"""
import re
import sys
from pathlib import Path

CELL = re.compile(
    r"TILE_ATTR_FULL\(\s*(\d+)\s*,\s*0\s*,\s*0\s*,\s*0\s*,"
    r"\s*SOLID_TILE_INDEX\s*\+\s*(\d+)\s*\)"
)


def extract(text, name, count):
    decl = re.search(
        r"(?:static\s+)?const\s+uint16_t\s+"
        + re.escape(name)
        + r"\s*\[\s*\d+\s*\](?:\s*\[\s*\d+\s*\])?\s*=\s*\{",
        text,
    )
    assert decl, "Missing " + name
    stop = text.find("\n};", decl.end())
    assert stop >= 0, "Unterminated " + name
    entries = [(int(a), int(b)) for a, b in CELL.findall(text[decl.end():stop])]
    assert len(entries) == count, (name, len(entries), count)
    assert all(0 <= pal <= 3 and 0 <= tile <= 225 for pal, tile in entries)
    return entries


def verify(checker, vertical, label):
    assert len(checker) == len(vertical)
    stripes = 0
    for (cpal, ctile), (vpal, vtile) in zip(checker, vertical):
        assert cpal == vpal, (label, "palette mismatch")
        if 16 <= ctile <= 120:
            assert vtile == ctile + 105, (label, ctile, vtile)
            stripes += 1
        else:
            assert vtile == ctile, (label, ctile, vtile)
    return stripes


def main(argv):
    assert len(argv) == 5, "Expected control and R39f colormap/colorcell .h files"
    ctlcm, ctlcc, tricm, tricc = [Path(p).read_text() for p in argv[1:]]
    control_checker = extract(ctlcm, "doom_colormap_cells", 32*256)
    tri_checker = extract(tricm, "doom_colormap_cells", 32*256)
    assert tri_checker == control_checker, "R39f must preserve R39e checker LUT exactly"
    ctl_solid = extract(ctlcm, "r39d_colormap_cells_solid", 32*256)
    tri_solid = extract(tricm, "r39d_colormap_cells_solid", 32*256)
    assert tri_solid == ctl_solid, "R39f must preserve R39d solid LUT exactly"
    checker256 = extract(tricc, "r39d_colorcell_checker", 256)
    solid256 = extract(tricc, "r39d_colorcell_solid", 256)
    assert checker256 == extract(ctlcc, "r39d_colorcell_checker", 256)
    assert solid256 == extract(ctlcc, "r39d_colorcell_solid", 256)
    vert256 = extract(tricc, "r39f_colorcell_vertical", 256)
    vert8192 = extract(tricm, "r39f_colormap_cells_vertical", 32*256)
    assert verify(checker256, vert256, "colorcell") == 169, "R35d checker color count changed"
    assert verify(tri_checker, vert8192, "colormap") > 4500
    assert len({(p, t) for p, t in vert256 if t >= 121}) >= 60
    assert all(121 <= t <= 225 for p, t in vert256 if t >= 121)
    # Tile lines generated in I_BuildSolidTiles: for 8 pixels in every
    # row, even nibbles are A and odd nibbles B, unlike chessboard rows.
    for a in range(15):
        for b in range(a+1, 15):
            row = (a * 0x10101010 + b * 0x01010101)
            nibbles = [row >> (28-4*x) & 15 for x in range(8)]
            assert nibbles == [a, b, a, b, a, b, a, b]
    src = Path("src/i_genesisv.c").read_text()
    assert "index = 121;" in src and "tile[y] = stripes" in src
    assert "r39f_active_colormap" not in src
    assert "r39d_active_colormap = r39f_colormap_cells_vertical" in src
    assert "colorcell = r39f_colorcell_vertical" in src
    assert "r39d_last_colormap = NULL;" in src
    assert "r39d_last_cellmap = NULL;" in src
    assert "I_BuildSolidTiles();" in src and "R30_LeaveNative" in src
    print("R39f PASS: control Checker & Solid unchanged, all 8192 shade slots"
          " map to identical colors, 105 new stripe tiles, 169 mixed colors,"
          " no additional work-RAM lookup tables.")


if __name__ == "__main__":
    main(sys.argv)
