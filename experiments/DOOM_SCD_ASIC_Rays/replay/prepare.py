"""Pack private E1M1 walls and real query vectors for the isolated cartridge."""
import json
import math
from pathlib import Path
import struct
import sys

wad_path, queries_path, output = map(Path, sys.argv[1:4])
selection = sys.argv[4] if len(sys.argv) == 5 else "first"
assert selection in ("first", "mixed")
wad = wad_path.read_bytes()
tag, count, directory = struct.unpack_from("<4sii", wad)
assert tag in (b"IWAD", b"PWAD")
lumps = list(struct.iter_unpack("<ii8s", wad[directory:directory + count * 16]))
start = next(i for i, (_, _, name) in enumerate(lumps) if name.rstrip(b"\0") == b"E1M1")
level = {name.rstrip(b"\0"): wad[pos:pos + size] for pos, size, name in lumps[start + 1:start + 11]}
vertices = list(struct.iter_unpack("<hh", level[b"VERTEXES"]))
lines = list(struct.iter_unpack("<7H", level[b"LINEDEFS"]))
recorded = json.loads(queries_path.read_text())
if selection == "mixed":
    clear = [q for q in recorded if q[5]][:128]
    blocked = [q for q in recorded if not q[5]][:256 - len(clear)]
    queries = sorted(clear + blocked, key=lambda q: q[0])
else:
    queries = recorded[:256]
assert len(queries) == 256
SCALE = 8
min_x = min([p[0] for p in vertices] + [q[i] >> 16 for q in queries for i in (1, 3)]) // SCALE * SCALE - 16
min_y = min([p[1] for p in vertices] + [q[i] >> 16 for q in queries for i in (2, 4)]) // SCALE * SCALE - 16


def mark(x, y):
    assert 0 <= x < 4096 and 0 <= y < 4096
    tiles.setdefault((x >> 5, y >> 5), bytearray(512))
    tile = tiles[x >> 5, y >> 5]
    offset = ((x & 31) >> 3) * 128 + (y & 31) * 4 + ((x & 7) >> 1)
    tile[offset] |= 1 << (0 if x & 1 else 4)


tiles = {}
for a, b, flags, _, _, _, back in lines:
    if flags & 4 and back != 0xffff:
        continue
    x1, y1 = vertices[a]
    x2, y2 = vertices[b]
    x1, x2 = (x1 - min_x) // SCALE, (x2 - min_x) // SCALE
    y1, y2 = (y1 - min_y) // SCALE, (y2 - min_y) // SCALE
    dx, dy = x2 - x1, y2 - y1
    n = max(abs(dx), abs(dy), 1)
    for i in range(n + 1):
        x, y = x1 + round(i * dx / n), y1 + round(i * dy / n)
        mark(x, y)
        mark(x + int(abs(dy) > abs(dx)), y + int(abs(dx) >= abs(dy)))

stamps = {bytes(512): 0}
stamp_map = [0] * (128 * 128)
for (x, y), tile in sorted(tiles.items()):
    index = stamps.setdefault(bytes(tile), len(stamps))
    stamp_map[y * 128 + x] = index * 4
assert len(stamps) * 512 <= 0x10000, len(stamps)
batches = bytearray()
for offset in range(0, len(queries), 64):
    vectors = bytearray()
    width = 0
    for _, x1, y1, x2, y2, visible in queries[offset:offset + 64]:
        x1, x2 = [(x - min_x * 65536) // 65536 for x in (x1, x2)]
        y1, y2 = [(y - min_y * 65536) // 65536 for y in (y1, y2)]
        # In 13.3 coordinates one map unit is one eighth pixel at this scale.
        assert all(0 <= p < 32768 for p in (x1, y1, x2, y2))
        steps = max(1, math.ceil(max(abs(x2 - x1), abs(y2 - y1)) / 8))
        assert steps + 1 <= 511
        dx, dy = [round(delta * 256 / steps) for delta in (x2 - x1, y2 - y1)]
        vectors += struct.pack(">HHhhHH", x1, y1, dx, dy, steps, visible)
        width = max(width, steps + 1)
    batches += struct.pack(">H", width) + vectors
assets = (struct.pack(">H", len(stamps) * 256) + b"".join(stamps) +
          struct.pack(">16384H", *stamp_map) + batches)
output.write_bytes(assets)
print(f"Packed {len(stamps)} stamps and 256 native E1M1 sight calls ({len(assets)} bytes). "
      f"Selection {selection}, tics {queries[0][0]}–{queries[-1][0]}, "
      f"{sum(q[5] for q in queries)} visible out of {sum(q[5] for q in recorded)} in capture.")
