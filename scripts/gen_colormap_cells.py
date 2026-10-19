#!/usr/bin/env python3
"""Generate a ROM-resident Doom COLORMAP -> Mega Drive tile-word lookup.

Must run after repack_wad.py and genpal.py. No extra 68000 RAM is allocated.
Uses exactly the same genpal_cell[] mapping as the existing rendering path.
"""
from pathlib import Path
import re
import struct
import os
import genpal

ROOT = Path(__file__).resolve().parent.parent
WAD = ROOT / "scripts" / "doom64_aligned.wad"
PALETTE = ROOT / "src" / "gen_pal.h"
OUT = ROOT / "src" / "colormap_cells.h"

def read_colormap(wad):
    data = wad.read_bytes()
    if data[:4] not in (b"IWAD", b"PWAD"):
        raise ValueError("Unsupported WAD magic")
    num_lumps = struct.unpack_from(">H", data, 4)[0]
    directory = struct.unpack_from(">I", data, 8)[0]
    if directory + 16 * num_lumps > len(data):
        raise ValueError("Invalid WAD directory")
    for i in range(num_lumps):
        pos = directory + 16 * i
        filepos = struct.unpack_from(">I", data, pos)[0]
        size = struct.unpack_from(">H", data, pos + 4)[0]
        name = data[pos + 8:pos + 16].split(b"\0")[0]
        if name == b"COLORMAP":
            if size < 32 * 256 or filepos + size > len(data):
                raise ValueError(f"Unexpected COLORMAP size: {size}")
            return data[filepos:filepos + 32 * 256]
    raise ValueError("COLORMAP lump not found")

def read_slots(palette):
    source = palette.read_text(encoding="utf-8")
    match = re.search(r"genpal_cell\s*\[256\]\s*=\s*\{([^}]*)\}", source, re.S)
    if not match:
        raise ValueError("Could not locate generated genpal_cell[256]")
    slots = [int(n) for n in re.findall(r"\b\d+\b", match.group(1))]
    if len(slots) != 256 or any(not 0 <= s < 56 for s in slots):
        raise ValueError("Unexpected genpal_cell layout")
    return slots

def checker_slots():
    source = PALETTE.read_text(encoding="utf-8")
    block = re.search(r"genpal_cram\[GENPAL_NSUB\]\[64\]\s*=\s*\{\s*\{([^}]*)\}", source, re.S)
    if not block:
        raise ValueError("Missing CRAM bank 0")
    words = [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", block.group(1))]
    if len(words) != 64:
        raise ValueError("Expected 64 CRAM entries")
    palette = [genpal.gen_to_rgb(w) for w in words]
    original = genpal.decode_subpal(genpal.load_playpal(), 0)
    choices = []
    for bank in range(4):
        for a in range(15):
            choices.append((bank, a, a, palette[bank*16+a]))
            for b in range(a+1, 15):
                rgb = tuple((palette[bank*16+a][i]+palette[bank*16+b][i])/2 for i in range(3))
                choices.append((bank, a, b, rgb))
    selected = []
    for rgb in original:
        def score(c):
            bank,a,b,display = c
            err = genpal.dist2(rgb, display)
            contrast = genpal.dist2(palette[bank*16+a], palette[bank*16+b])
            return err  # R35d strong 50/50 mixing: select closest displayed RGB
        bank,a,b,_ = min(choices, key=score)
        tile = a if a == b else 16 + sum(14-k for k in range(a)) + (b-a-1)
        selected.append((bank,tile))
    return selected

def main():
    colors = read_colormap(WAD)
    slots = read_slots(PALETTE)
    checker = os.environ.get('DOOM_R35D_CHECKER') == '1'
    runtime = os.environ.get('DOOM_R39D_DITHER_TOGGLE') == '1'
    if runtime and not checker:
        raise RuntimeError("R39d runtime toggle requires R35d checker tables")
    lookup = checker_slots() if checker else None
    if checker:
        from collections import Counter
        import json
        selected = [t >= 16 for bank,t in lookup]
        checker_colormap = sum(selected[i] for i in colors[:32*256])
        checker_count = sum(selected)
        pairs_used = len({(bank,t) for bank,t in lookup if t >= 16})
        report = {
            "mode": "r35d-checker-strong",
            "checker_colors": checker_count,
            "total_colors": 256,
            "checker_colormap_cells": checker_colormap,
            "total_colormap_cells": 8192,
            "unique_checker_tiles": pairs_used,
            "checker_per_shade": [sum(selected[i] for i in colors[shade*256:(shade+1)*256]) for shade in range(32)],
            "checker_tile_min": 16,
            "checker_tile_max": 120,
            "solid_tile_min": 0,
            "solid_tile_max": 15,
            "palettes": 4,
        }
        print("R35D CHECKER AUDIT: " + json.dumps(report, sort_keys=True))
        target = os.environ.get("DOOM_R35D_REPORT")
        if target:
            Path(target).write_text(json.dumps(report, indent=2) + "\n")
        if checker_count < 140 or checker_colormap < 4500 or pairs_used < 60:
            raise RuntimeError("R35d: dithering LUT ineffective; rejecting ROM")
    def emit_colorcell(name, pairs):
        cells = ['/* Automatically generated tile words for Doom colors. */',
                 f'static const uint16_t {name}[256] = {{']
        for pal,tile in pairs:
            cells.append(f'TILE_ATTR_FULL({pal},0,0,0,SOLID_TILE_INDEX + {tile}),')
        cells.append('};')
        return cells

    solid_pairs = [(slot // 14, 1 + slot % 14) for slot in slots]
    if runtime:
        cells = emit_colorcell('r39d_colorcell_checker', lookup)
        cells += emit_colorcell('r39d_colorcell_solid', solid_pairs)
        cells.append('const uint16_t *colorcell = r39d_colorcell_checker;')
    else:
        cells = ['/* Generated exact colorcell mapping; SGDK indices resolved by C. */',
                 'const uint16_t colorcell[256] = {']
        for i,slot in enumerate(slots):
            pal,tile = lookup[i] if checker else solid_pairs[i]
            cells.append(f'TILE_ATTR_FULL({pal},0,0,0,SOLID_TILE_INDEX + {tile}),')
        cells.append('};')
    (ROOT / 'src/r20_colorcell.h').write_text('\\n'.join(cells)+'\\n')

    def make_colormap_rows(pairs):
        rows = []
        for shade in range(32):
            row = []
            for source in colors[shade * 256:(shade + 1) * 256]:
                pal,tile = pairs[source]
                row.append(f'TILE_ATTR_FULL({pal}, 0, 0, 0, SOLID_TILE_INDEX + {tile})')
            rows.append('  {')
            for offset in range(0, 256, 8):
                rows.append('    ' + ', '.join(row[offset:offset + 8]) + ',')
            rows.append('  },')
        return rows

    lines = [
        "/* Automatically generated by scripts/gen_colormap_cells.py. */",
        "#ifndef DOOM_COLORMAP_CELLS_H",
        "#define DOOM_COLORMAP_CELLS_H",
        "static const uint16_t doom_colormap_cells[32][256] = {",
    ]
    lines += make_colormap_rows(lookup if checker else solid_pairs)
    lines.append("};")
    if runtime:
        lines.append("static const uint16_t r39d_colormap_cells_solid[32][256] = {")
        lines += make_colormap_rows(solid_pairs)
        lines.append("};")
    lines += ["#endif", ""]
    OUT.write_text('\\n'.join(lines), encoding="utf-8")
    print(f"Generated ROM-only colormap LUT: {32768 if runtime else 16384} bytes; no extra 68000 RAM")

if __name__ == "__main__":
    main()
