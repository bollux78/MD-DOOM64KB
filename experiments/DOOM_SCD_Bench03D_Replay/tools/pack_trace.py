#!/usr/bin/env python3
"""Pack the private R128 trace and extract the actual linked column kernels."""
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
import sys

ref, rom, elf, nm = map(Path, sys.argv[1:])
out = Path("build")
out.mkdir(exist_ok=True)
trace = json.loads((ref / "column-trace.json").read_text())
entries = trace["frames"]
assert list(map(int, entries)) == [200, 210, 220, 230, 237, 245, 252, 260]
textures = {key: i for i, key in enumerate(trace["textures"])}
luts = {key: i for i, key in enumerate(trace["palettes"])}
image = bytearray(4 * (2 + len(entries) + len(luts)))

def addr(slot):
    struct.pack_into(">I", image, slot * 4, len(image))

addr(0)
for tex in trace["textures"].values():
    tex = bytes.fromhex(tex)
    assert len(tex) == 128
    image.extend(tex)

# R113 addresses its high-nibble table exactly 8704 bytes after the low table.
# 34 low tables fit in that interval and share one equally sized high slab.
palette_data = list(trace["palettes"].values())
for base in range(0, len(palette_data), 34):
    group = palette_data[base:base+34]
    start = len(image)
    image.extend(bytes(2 * 8704))
    for local, colors in enumerate(group):
        low, high = bytes.fromhex(colors[:512]), bytes.fromhex(colors[512:])
        index = start + local * 256
        struct.pack_into(">I", image, (10 + base + local) * 4, index)
        image[index:index+256] = low
        image[index+8704:index+8960] = high
struct.pack_into(">I", image, 4, 40)  # palette pointer table

for index, (tic, calls) in enumerate(entries.items()):
    reference = (ref / f"r128-e1m1-tic-{tic}.bin").read_bytes()
    assert len(reference) == 3344
    mask, ink = bytearray(3344), bytearray(3344)
    packed = bytearray()
    for call in calls:
        before, after = (bytes.fromhex(call[key]) for key in ("before", "after"))
        flags = call["odd"] | (2 if call["kernel"] == "R113_WallColumn" else 0)
        packed.extend(struct.pack(">HHHHHBB", call["offset"], call["phase"], call["step"],
                                  textures[call["source"]], luts[call["palette"]],
                                  call["count"], flags))
        packed.extend(before.ljust(23, b'\0'))
        packed.extend(after.ljust(23, b'\0'))
        for row in range(call["count"]):
            y = row + call["odd"]
            pos = call["offset"] + 152 * (y // 2)
            nibble = 0x0f if y & 1 else 0xf0
            mask[pos] |= nibble
            ink[pos] = (ink[pos] & ~nibble) | (after[y // 2] & nibble)
    # Remove coverage where a later, untraced pass replaced the kernel output.
    for i in range(len(mask)):
        mismatch = ink[i] ^ reference[i]
        if mismatch & 0xf0:
            mask[i] &= 0x0f
        if mismatch & 0x0f:
            mask[i] &= 0xf0
    nibbles = sum(bool(v & 0x0f) + bool(v & 0xf0) for v in mask)
    assert nibbles
    addr(2 + index)
    image.extend(struct.pack(">HH", int(tic), len(calls)))
    image.extend(reference)
    image.extend(mask)
    image.extend(packed)
    print(f"FRAME {tic}: {len(calls)} calls; {nibbles} output nibbles from replay")
(out / "fixture.bin").write_bytes(image)
print("FIXTURE:", len(image), "bytes", len(textures), "textures", len(luts), "palettes")

rom = rom.read_bytes()
symbols = subprocess.check_output([nm, "-S", elf], text=True)
for kernel in ("R60_WallColumn", "R113_WallColumn"):
    (address, size, _, _), = [line.split() for line in symbols.splitlines()
                              if line.split()[-1:] == [kernel]]
    address, size = int(address, 16), int(size, 16)
    code = rom[address:address + size]
    assert len(code) == size and 100 <= size <= 256 and code[-2:] == b'\x4e\x75'
    (out / (kernel + ".bin")).write_bytes(code)
    print(kernel, len(code), sha256(code).hexdigest())
