"""Compose Doom wall patches and quantize their RGB colors for the Genesis VDP."""
import math
import struct

COLORS = (0x000, 0x844, 0x246, 0x08E, 0x04C, 0x26A, 0x48C, 0xE0E,
          0x222, 0x444, 0x666, 0x888, 0xCCC, 0x248, 0x462, 0xC84)


def name(raw):
    return raw.split(b"\0", 1)[0].decode("ascii").upper()


def compose(lumps, patches, definition):
    width, height, layers = definition
    pixels = bytearray(width * height)
    for ox, oy, index in layers:
        patch = lumps[patches[index]]
        pw, _, _, _ = struct.unpack_from("<hhhh", patch)
        for x in range(pw):
            tx = ox + x
            if not 0 <= tx < width:
                continue
            pos, = struct.unpack_from("<I", patch, 8 + 4 * x)
            while patch[pos] != 255:
                y, length = patch[pos:pos + 2]
                for row, pixel in enumerate(patch[pos + 3:pos + 3 + length], oy + y):
                    if 0 <= row < height:
                        pixels[tx * height + row] = pixel
                pos += length + 4
    return pixels


def materials(entries, map_name):
    lumps = {key.upper(): data for key, data in entries}
    start = max(i for i, (key, _) in enumerate(entries) if key == map_name)
    level = dict(entries[start + 1:start + 9])
    sides = list(struct.iter_unpack("<hh8s8s8sH", level["SIDEDEFS"]))
    vertices = list(struct.iter_unpack("<hh", level["VERTEXES"]))
    lines = list(struct.iter_unpack("<7H", level["LINEDEFS"]))
    definitions = {}
    for key in ("TEXTURE1", "TEXTURE2"):
        if key not in lumps:
            continue
        data = lumps[key]
        count, = struct.unpack_from("<I", data)
        for offset, in struct.iter_unpack("<I", data[4:4 + 4 * count]):
            raw, _, width, height, _, layers = struct.unpack_from("<8sIhhIh", data, offset)
            records = [struct.unpack_from("<hhHhh", data, offset + 22 + i * 10)[:3]
                       for i in range(layers)]
            definitions[name(raw)] = width, height, records
    raw = lumps["PNAMES"]
    count, = struct.unpack_from("<I", raw)
    patches = [name(raw[4 + 8 * i:12 + 8 * i]) for i in range(count)]
    rgb = list(struct.iter_unpack("BBB", lumps["PLAYPAL"][:768]))
    converted = {i: tuple(((color >> shift) & 14) * 255 // 14 for shift in (0, 4, 8))
                 for i, color in enumerate(COLORS) if i != 7}
    translate = bytes(min(converted, key=lambda i: sum((a - b) ** 2 for a, b in zip(c, converted[i])))
                      or 8 for c in rgb)
    keys = sorted({name(k) for side in sides for k in side[2:5]} - {"-"})
    ids = {key: i + 1 for i, key in enumerate(keys)}
    images = []
    for key in keys:
        definition = definitions[key]
        images.append((key, *definition[:2], compose(lumps, patches, definition).translate(translate)))
    segments = []
    for a, b, _, line, direction, offset in struct.iter_unpack("<6H", level["SEGS"]):
        row = lines[line]
        xoff, yoff, upper, lower, middle, _ = sides[row[5 + direction]]
        ax, ay = vertices[a]
        bx, by = vertices[b]
        length = round(math.hypot(bx - ax, by - ay) * 256)
        segments.append(((xoff + offset) * 256, length, yoff, row[2] & 24,
                         ids.get(name(middle), 0), ids.get(name(upper), 0), ids.get(name(lower), 0)))
    return images, segments


def emit(entries, map_name, target):
    images, segments = materials(entries, map_name)
    lines = ['#include "nexus.h"', '']
    for i, (_, _, _, pixels) in enumerate(images, 1):
        lines.append(f"static const uint8_t texture_{i}[] = {{")
        for offset in range(0, len(pixels), 32):
            lines.append("    " + ", ".join(map(str, pixels[offset:offset + 32])) + ",")
        lines.append("};")
    lines.extend(["const NxTexture nexus_textures[] = {", "    {0, 0, 0},"])
    for i, (_, width, height, _) in enumerate(images, 1):
        lines.append(f"    {{texture_{i}, {width}, {height}}},")
    lines.extend(["};", "const NxMaterial nexus_materials[] = {"])
    for row in segments:
        lines.append("    {" + ", ".join(map(str, row)) + "},")
    lines.extend(["};", "const uint16_t nexus_palette[16] = {" + ", ".join(map(str, COLORS)) + "};"])
    target.write_text("\n".join(lines) + "\n")
