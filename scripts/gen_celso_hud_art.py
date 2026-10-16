#!/usr/bin/env python3
"""Re-quantize selected MegalDoom Doom HUD art for our existing 56-color CRAM.

The upstream MegalDoom HUD uses dedicated PAL0/1/2. Our existing engine
uses all four palettes for its 56-color 3D picture. NEVER overwrite
gen_pal.h, modify those palettes or confine world rendering to PAL3 here.
All art is converted once on the host, not per-frame on the Mega Drive.

Source data in assets/celso-megaldoom-hud-source.json is extracted from
celsowm/megaldoom (MIT, Celso Fontes 2026); original Doom artwork rights
remain with their respective owners.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "celso-megaldoom-hud-source.json"
PALETTE = ROOT / "src" / "gen_pal.h"
OUTPUT = ROOT / "src" / "doom_wad_hud_tiles.h"

BG_W = 38
BG_H = 4
BG_COUNT = BG_W * BG_H   # 152 cropped from Celso's original 40×4 tile STBAR
FACE_COUNT = 16         # fixed 4x4 32x32 portrait
DIGIT_COUNT = 10 * 4    # 10 original 16x16 glyphs; 4 tiles each
KEY_COUNT = 3           # three 7x5 icon tiles
TOTAL = BG_COUNT + FACE_COUNT + DIGIT_COUNT + KEY_COUNT  # 211


def rgb(hex24):
    return ((hex24 >> 16) & 255, (hex24 >> 8) & 255, hex24 & 255)


def parse_cram():
    text = PALETTE.read_text(encoding="utf-8")
    marker = "genpal_cram[GENPAL_NSUB][64]"
    start = text.index(marker)
    open0 = text.index("{", start)
    open1 = text.index("{", open0 + 1)
    stop = text.index("}", open1)
    words = [int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]+", text[open1:stop])]
    assert len(words) == 64, "genpal.h: invalid Genesis palette"
    def unpack(w):
        def channel(shift):
            c = (w >> shift) & 7
            return (c << 5) | (c << 2) | (c >> 1)
        return channel(1), channel(5), channel(9)
    return [[unpack(w) for w in words[p*16:p*16+16]] for p in range(4)]


def decode_tile(hexrows, palette):
    assert len(hexrows) == 8
    out = []
    for row in hexrows:
        n = int(row, 16)
        for x in range(8):
            index = (n >> (28 - 4*x)) & 0xF
            out.append(rgb(palette[index]))
    return out


def quantize(tile_pixels, cram):
    assert len(tile_pixels) == 64
    best = None
    for pal_id, pal in enumerate(cram):
        indices = []
        error = 0
        for pixel in tile_pixels:
            # Keep zero the universal black index. The SGDK font uses
            # index15 in every bank; don't use that reserved text index.
            if max(pixel) <= 12:
                chosen, dist = 0, 0
            else:
                candidates = [
                    sum((pixel[ch] - pal[i][ch]) ** 2 for ch in range(3))
                    for i in range(1, 15)
                ]
                chosen = 1 + min(range(14), key=candidates.__getitem__)
                dist = candidates[chosen - 1]
            error += dist
            indices.append(chosen)
        if best is None or error < best[0]:
            best = (error, pal_id, indices)
    _, pal_id, indices = best
    rows = []
    for y in range(8):
        packed = 0
        for x in range(8):
            packed = (packed << 4) | indices[y*8 + x]
        rows.append(packed)
    return pal_id, rows


def source_pixels():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    assert src["upstream"] == "celsowm/megaldoom"
    assert len(src["hud_tiles_rows"]) == 160 * 8
    assert len(src["face_neutral_rows"]) == 16 * 8
    assert len(src["digit_pixels"]) == 11 * 16 * 16
    assert len(src["digit_widths"]) == 11
    assert len(src["key_pixels"]) == 3 * 5 * 7
    barpal = src["palette_hud"]
    facepal = src["palette_face"]
    digitpal = src["palette_digits"]
    pixels = []

    # Crop 8px from each border of MegalDoom's 320x32 STBAR.
    # Original 32px face remains pixel-centered (column 17 of 38).
    for ty in range(BG_H):
        for tx in range(1, 39):
            index = ty*40 + tx
            pixels.append(decode_tile(
                src["hud_tiles_rows"][index*8:index*8+8], barpal
            ))
    assert len(pixels) == BG_COUNT

    # Neutral face frame0 from the source's 16 8x8 pieces, unchanged
    # geometry. Skin-tone fidelity depends on our shared world palette.
    for tile in range(16):
        pixels.append(decode_tile(
            src["face_neutral_rows"][tile*8:tile*8+8], facepal
        ))

    # Native Doom red glyphs from Celso's 16x16 pixel canvases, not the
    # earlier 8x16 screenshot thumbnails. Four 8x8 VDP tiles per digit.
    for digit in range(10):
        arr = src["digit_pixels"][digit*256:(digit+1)*256]
        for ty in range(2):
            for tx in range(2):
                pixels.append([
                    rgb(digitpal[arr[(ty*8+y)*16+tx*8+x]])
                    for y in range(8) for x in range(8)
                ])

    # Native 7x5 keycard patches: 1 tile each. Black index0 background.
    for key in range(3):
        arr = src["key_pixels"][key*35:(key+1)*35]
        pixels.append([
            rgb(barpal[arr[y*7+x]]) if y < 5 and x < 7 else (0,0,0)
            for y in range(8) for x in range(8)
        ])
    assert len(pixels) == TOTAL
    return pixels


def main():
    source = source_pixels()
    cram = parse_cram()
    tiles = [quantize(p, cram) for p in source]
    assert len(tiles) == TOTAL
    header = [
        "/* AUTO-GENERATED by scripts/gen_celso_hud_art.py.",
        " * Doom artwork extracted from celsowm/megaldoom (MIT source;",
        " * Copyright 2026 Celso Fontes). Original art rights reserved.",
        " * Converted to existing 56-color world CRAM: no CRAM changes.",
        " * BG 152 / neutral face 16 / large 16x16 digits 40 / keys 3.",
        " */",
        "#ifndef DOOM_WAD_HUD_TILES_H",
        "#define DOOM_WAD_HUD_TILES_H",
        "#define DOOM_WAD_HUD_TOTAL_TILES 211",
        "#define DOOM_WAD_HUD_BG_TILES 152",
        "#define DOOM_WAD_HUD_FACE_OFFSET 152",
        "#define DOOM_WAD_HUD_DIGIT_OFFSET 168",
        "#define DOOM_WAD_HUD_KEY_OFFSET 208",
        "static const uint8_t doom_wad_hud_pal[211] = {",
    ]
    for i in range(0, TOTAL, 16):
        header.append("    " + ",".join(str(pal) for pal, _ in tiles[i:i+16]) + ",")
    header += ["};", "static const uint32_t doom_wad_hud_words[211][8] = {"]
    for _, rows in tiles:
        header.append("    {" + ",".join(f"0x{v:08X}u" for v in rows) + "},")
    header += ["};", "#endif", ""]
    OUTPUT.write_text("\n".join(header), encoding="ascii")
    print("MegalDoom original HUD art: 211 tiles, 6752 bytes VRAM")
    print("Source: Celso STBAR 320→304, neutral 32x32 face, 16x16 Doom numbers, 7x5 keys")
    print("World palette retained: full original 56-color CRAM (4 x 14 colors)")
    print("Generated:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
