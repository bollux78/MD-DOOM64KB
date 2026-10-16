#!/usr/bin/env python3
"""Build exact 8x8 Mega Drive tile graphics for the Doom HUD v1.

Preferred source: original status-bar patches from the reduced WAD, if
present in classic Doom patch format. Fallback source: a small quantized
copy of the ORIGINAL Doom sprite atlas supplied by the user, embedded as
three text assets. No download, Pillow, or image editor is needed.
This is a deliberately fast visual integration, not the final Dither Lab.
"""
from __future__ import annotations
import base64
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets"
OUT = ROOT / "src" / "doom_wad_hud_tiles.h"

W = 304
H = 32
BW = W // 8
BH = H // 8
BG_TILES = BW * BH                 # 152
FACE_TILES = 16                   # 4x4
DIGIT_TILES = 20                  # 10 digits x 2 vertical tiles
TOTAL_TILES = BG_TILES + FACE_TILES + DIGIT_TILES
assert TOTAL_TILES == 188

# RGB palettes from the user-provided original Doom HUD reference montage.
BG_PALETTE = (
    (113,113,113), (85,85,85), (72,72,72), (40,40,40)
)
FACE_PALETTE = (
    (239,180,144), (229,153,105), (200,132,88), (177,114,70),
    (158,108,69), (155,99,59), (143,95,55), (135,87,51),
    (119,79,43), (93,93,93), (107,71,39), (95,67,35),
    (83,63,31), (65,50,26), (36,36,36), (33,27,18)
)
DIGIT_PALETTE = (
    (197,0,0), (169,0,0), (137,32,32), (153,0,0),
    (139,0,0), (95,26,26), (98,6,6), (121,0,0),
    (104,0,0), (83,0,0), (67,0,0), (40,63,63),
    (49,48,48), (58,34,34), (60,18,18), (0,0,0)
)


def pixels_from_reference(filename: str, expected: int, palette):
    buf = zlib.decompress(base64.b85decode(
        (SRC / filename).read_text(encoding="ascii").strip().encode("ascii")
    ))
    if len(buf) != expected:
        raise ValueError(f"{filename}: expected {expected} pixels, got {len(buf)}")
    if any(b >= len(palette) for b in buf):
        raise ValueError(f"{filename}: index exceeds {len(palette)}-color palette")
    return [palette[b] for b in buf]


def read_reduced_wad():
    path = ROOT / "scripts" / "doom64_aligned.wad"
    if not path.is_file():
        path = ROOT / "scripts" / "doom64.wad"
    data = path.read_bytes()
    if len(data) < 12:
        raise ValueError("WAD truncated")
    # This port repacks its Neo Geo Doom WAD with a big-endian directory.
    count = struct.unpack_from(">h", data, 4)[0]
    directory = struct.unpack_from(">I", data, 8)[0]
    if count <= 0 or count > 10000 or directory + 16 * count > len(data):
        raise ValueError("Invalid WAD directory")
    lumps = {}
    for i in range(count):
        offset = directory + i * 16
        fp, size = struct.unpack_from(">IH", data, offset)
        name = data[offset + 8:offset + 16].split(b"\0")[0].decode("ascii", "replace").upper()
        if size and fp + size <= len(data):
            lumps[name] = data[fp:fp + size]
    return lumps


def patch(data: bytes):
    """Decode an ordinary Doom picture patch (not a flat or sprite atlas)."""
    if not data or len(data) < 12:
        raise ValueError("patch missing or truncated")
    width, height, left, top = struct.unpack_from("<HHhh", data, 0)
    if not 1 <= width <= 640 or not 1 <= height <= 256:
        raise ValueError("not a classic Doom picture patch")
    if len(data) < 8 + 4 * width:
        raise ValueError("patch column offsets truncated")
    rgba_indices = [-1] * (width * height)
    for x in range(width):
        pos = struct.unpack_from("<I", data, 8 + 4 * x)[0]
        if pos >= len(data):
            raise ValueError("invalid patch column")
        posts = 0
        while True:
            if pos >= len(data):
                raise ValueError("unterminated patch column")
            topdelta = data[pos]
            if topdelta == 255:
                break
            if pos + 4 > len(data):
                raise ValueError("truncated patch post")
            length = data[pos + 1]
            if pos + 4 + length > len(data):
                raise ValueError("truncated patch pixel data")
            for y in range(length):
                if topdelta + y < height:
                    rgba_indices[(topdelta + y) * width + x] = data[pos + 3 + y]
            pos += length + 4
            posts += 1
            if posts > height * 2 + 16:
                raise ValueError("suspicious number of Doom patch posts")
    return width, height, rgba_indices


def playpal_rgb(packed):
    if not packed or len(packed) < 512:
        raise ValueError("Neo Geo PLAYPAL missing")
    rgb = []
    for i in range(256):
        word = struct.unpack_from(">H", packed, 2 * i)[0]
        dark = (word >> 15) & 1
        def one(four, low):
            six = (four << 2) | (low << 1) | dark
            return (six << 2) | (six >> 4)
        rgb.append((
            one((word >> 8) & 15, (word >> 14) & 1),
            one((word >> 4) & 15, (word >> 13) & 1),
            one(word & 15, (word >> 12) & 1),
        ))
    return rgb


def doom_rgb_patch(decoded, palette, width, height, offset_x=0, offset_y=0):
    w, h, data = decoded
    out = [(0,0,0)] * (width * height)
    for y in range(height):
        sy = y + offset_y
        if not 0 <= sy < h:
            continue
        for x in range(width):
            sx = x + offset_x
            if not 0 <= sx < w:
                continue
            index = data[sy * w + sx]
            if index >= 0:
                out[y * width + x] = palette[index]
    return out


def wad_art_fallback():
    """Only use a WAD patch when all its inputs are valid, else use atlas."""
    bg = pixels_from_reference("doom-hud-bg.b85", W * H, BG_PALETTE)
    face = pixels_from_reference("doom-hud-face.b85", 32 * 32, FACE_PALETTE)
    digits = pixels_from_reference("doom-hud-digits.b85", 80 * 16, DIGIT_PALETTE)
    sources = ["atlas", "atlas", "atlas"]

    try:
        lumps = read_reduced_wad()
    except (OSError, ValueError) as exc:
        print("WAD HUD probe:", exc, "(using bundled Doom atlas)")
        return bg, face, digits, sources

    present = sorted(name for name in lumps if name.startswith(("STBAR", "STFST", "STTNUM")))
    print("Status graphics found in reduced WAD:", present[:25] if present else "none")

    try:
        pw, ph, _ = pic = patch(lumps["STBAR"])
        if pw >= 304 and ph >= 32:
            palette = playpal_rgb(lumps["PLAYPAL"])
            startx = (pw - 304) // 2
            bg = doom_rgb_patch(pic, palette, W, H, startx, 0)
            sources[0] = "WAD STBAR"
    except (KeyError, ValueError, IndexError, struct.error) as exc:
        print("Background: reference atlas (STBAR unavailable/unsupported)")

    try:
        name = next(name for name in ("STFST00", "STFST01", "STFST02") if name in lumps)
        pic = patch(lumps[name])
        pw, ph, _ = pic
        if pw > 32 or ph > 32:
            raise ValueError("unusually large portrait")
        palette = playpal_rgb(lumps["PLAYPAL"])
        face = doom_rgb_patch(pic, palette, 32, 32, -(32 - pw)//2, -(32 - ph)//2)
        sources[1] = "WAD " + name
    except (StopIteration, KeyError, ValueError, IndexError, struct.error):
        print("Portrait: reference atlas (STFST unavailable/unsupported)")

    try:
        palette = playpal_rgb(lumps["PLAYPAL"])
        out = [(0, 0, 0)] * (80 * 16)
        for num in range(10):
            pw, ph, patch_data = patch(lumps[f"STTNUM{num}"])
            if pw > 64 or ph > 32:
                raise ValueError("digit patch unexpectedly large")
            # nearest-neighbor resample for speed, not final Dither Lab quality
            for y in range(16):
                sy = min(ph - 1, y * ph // 16)
                for x in range(8):
                    sx = min(pw - 1, x * pw // 8)
                    idx = patch_data[sy * pw + sx]
                    if idx >= 0:
                        out[y * 80 + num * 8 + x] = palette[idx]
        digits = out
        sources[2] = "WAD STTNUM0-9"
    except (KeyError, ValueError, IndexError, struct.error):
        print("Digits: reference atlas (STTNUM0-9 unavailable/unsupported)")
    return bg, face, digits, sources


def read_genesis_palette():
    generated = (ROOT / "src" / "gen_pal.h").read_text(encoding="utf-8")
    marker = "genpal_cram[GENPAL_NSUB][64]"
    start = generated.index(marker)
    first = generated.index("{", start)
    next_open = generated.index("{", first + 1)
    end = generated.index("}", next_open)
    words = [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", generated[next_open:end])]
    if len(words) != 64:
        raise ValueError(f"Expected 64 colors, got {len(words)}")
    def unpack(word):
        return tuple((((word >> shift) & 7) << 5) | (((word >> shift) & 7) << 2) | (((word >> shift) & 7) >> 1)
                     for shift in (1, 5, 9))
    return [list(map(unpack, words[p*16:(p+1)*16])) for p in range(4)]


def quantize_tile(pixels, cram):
    """A tile can use exactly one 16-color VDP palette; choose the best."""
    best = None
    for pal, choices in enumerate(cram):
        indices = []
        error = 0
        for r, g, b in pixels:
            if r <= 12 and g <= 12 and b <= 12:
                idx, d = 0, 0
            else:
                distances = [
                    (r-c[0])**2 + (g-c[1])**2 + (b-c[2])**2
                    for c in choices
                ]
                idx = min(range(16), key=distances.__getitem__)
                d = distances[idx]
            indices.append(idx)
            error += d
        if best is None or error < best[0]:
            best = (error, pal, indices)
    _, pal, indices = best
    rows = []
    for y in range(8):
        word = 0
        for x in range(8):
            word = (word << 4) | indices[y * 8 + x]
        rows.append(word)
    return pal, rows


def main():
    bg, face, digit_atlas, sources = wad_art_fallback()
    cram = read_genesis_palette()
    source_tiles = []
    # 152 tile cells from 304x32 Doom status background.
    for ty in range(BH):
        for tx in range(BW):
            source_tiles.append([
                bg[(ty * 8 + py) * W + (tx * 8 + px)]
                for py in range(8) for px in range(8)
            ])
    # fixed neutral 32x32 portrait -> 4x4 tiles.
    for ty in range(4):
        for tx in range(4):
            source_tiles.append([
                face[(ty * 8 + py) * 32 + (tx * 8 + px)]
                for py in range(8) for px in range(8)
            ])
    # Doom's red number glyphs -> one 8x16 digit = 2 tiles.
    for digit in range(10):
        for ty in range(2):
            source_tiles.append([
                digit_atlas[(ty * 8 + py) * 80 + (digit * 8 + px)]
                for py in range(8) for px in range(8)
            ])
    assert len(source_tiles) == TOTAL_TILES
    converted = [quantize_tile(tile, cram) for tile in source_tiles]
    header = [
        "/* AUTO-GENERATED: DOOM HUD. scripts/gen_doom_wad_hud.py */",
        "/* Sources: background=%s, face=%s, digits=%s */" % tuple(sources),
        "#ifndef DOOM_WAD_HUD_TILES_H",
        "#define DOOM_WAD_HUD_TILES_H",
        "#define DOOM_WAD_HUD_TOTAL_TILES 188",
        "#define DOOM_WAD_HUD_BG_TILES 152",
        "#define DOOM_WAD_HUD_FACE_OFFSET 152",
        "#define DOOM_WAD_HUD_DIGIT_OFFSET 168",
        "static const uint8_t doom_wad_hud_pal[188] = {",
    ]
    for i in range(0, len(converted), 16):
        header.append("    " + ", ".join(str(p) for p, _ in converted[i:i+16]) + ",")
    header.append("};")
    header.append("static const uint32_t doom_wad_hud_words[188][8] = {")
    for pal, rows in converted:
        header.append("    {" + ",".join("0x%08Xu" % row for row in rows) + "},")
    header.extend(["};", "#endif", ""])
    OUT.write_text("\n".join(header), encoding="ascii")
    print("Doom HUD tiles:", TOTAL_TILES, "tiles,", 32 * TOTAL_TILES, "bytes VRAM")
    print("Sources:", ", ".join(sources))
    print("Output:", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
