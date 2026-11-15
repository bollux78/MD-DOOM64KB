#!/usr/bin/env python3
"""Intermission music: res/r25-inter.vgm -> inter_music.bin = u32 loop offset (big endian) + raw VGM command stream.
compose.py appends it as ROM bank 24 (0xC00000); the menu maps it at slot 7 (0x380000) during the intermission."""
import struct
d = open("/home/claude/md-doom64kb/res/r25-inter.vgm", "rb").read()
assert d[:4] == b"Vgm "
start = 0x34 + struct.unpack("<I", d[0x34:0x38])[0]
loop = 0x1c + struct.unpack("<I", d[0x1c:0x20])[0]
p = start
while d[p] != 0x66:   # walk the command stream to its end marker (drop the GD3 tag after it)
    b = d[p]
    p += 3 if b in (0x52, 0x53, 0x61) else 2 if b == 0x50 else 1
data = d[start:p + 1]
assert len(data) < 0x80000 - 4
open("inter_music.bin", "wb").write(struct.pack(">I", loop - start) + data)
print("inter_music.bin", len(data) + 4, "loop", loop - start)
