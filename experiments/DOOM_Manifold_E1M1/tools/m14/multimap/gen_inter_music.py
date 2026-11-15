#!/usr/bin/env python3
"""Intermission music: res/r25-inter.vgm -> inter_music.bin (placed at ROM 0x2F9600, see compose.py).
1. VGM command stream (YM2612 0x52/0x53, PSG 0x50, frame wait 0x62, end 0x66) without the header/GD3 tag.
2. YM writes that repeat the previous value of the same register are dropped (key-on 0x28 and the
   frequency registers 0xA0-0xAF are always kept: the A4/A0 pair latches on the A0 write).
3. LZ with a 16 KB window: groups of 8 items, flag byte (bit=1 literal byte, bit=0 match =
   u16 big-endian (distance-1) + u8 (length-4)).  The menu decodes it on the fly (lz_next in menu.c)."""
import struct
from collections import defaultdict
W, MINM, MAXM, CHAIN = 16384, 4, 259, 256
d = open("/home/claude/md-doom64kb/res/r25-inter.vgm", "rb").read()
assert d[:4] == b"Vgm "
p = 0x34 + struct.unpack("<I", d[0x34:0x38])[0]
loop_abs = 0x1c + struct.unpack("<I", d[0x1c:0x20])[0]
assert loop_abs == p, "loop point must be the start of the stream"
out = bytearray(); ym = {}
while d[p] != 0x66:
    b = d[p]
    if b in (0x52, 0x53):
        r, v = d[p+1], d[p+2]
        if (b == 0x52 and r == 0x28) or 0xA0 <= r <= 0xAF or ym.get((b, r)) != v:
            out += d[p:p+3]; ym[(b, r)] = v
        p += 3
    elif b == 0x50: out += d[p:p+2]; p += 2
    elif b == 0x62: out.append(b); p += 1
    else: raise SystemExit("unsupported VGM command %02x" % b)
out.append(0x66)
data = bytes(out); n = len(data); h = defaultdict(list); items = []; i = 0
def add(j):
    if j + 3 < n: h[data[j:j+4]].append(j)
while i < n:
    best = bo = 0
    if i + 3 < n:
        for j in reversed(h[data[i:i+4]][-CHAIN:]):
            if i - j > W: break
            l = 0
            while l < MAXM and i + l < n and data[j+l] == data[i+l]: l += 1
            if l > best: best, bo = l, i - j
            if best == MAXM: break
    if best >= MINM:
        items.append((1, bo, best))
        for k in range(best): add(i + k)
        i += best
    else:
        items.append((0, data[i], 0)); add(i); i += 1
enc = bytearray()
for k in range(0, len(items), 8):
    fb = 0; body = bytearray()
    for bit, (t, a, b) in enumerate(items[k:k+8]):
        if t == 0: fb |= 1 << bit; body.append(a)
        else: body += bytes([(a-1) >> 8, (a-1) & 255, b - MINM])
    enc.append(fb); enc += body
# self-check: decode like the 68000 ring-buffer decoder does
dec = bytearray(); s = 0
while len(dec) < n:
    fl = enc[s]; s += 1
    for bit in range(8):
        if len(dec) >= n: break
        if fl & (1 << bit): dec.append(enc[s]); s += 1
        else:
            o = ((enc[s] << 8) | enc[s+1]) + 1; l = enc[s+2] + MINM; s += 3
            for _ in range(l): dec.append(dec[-o])
assert bytes(dec[:n]) == data
open("inter_music.bin", "wb").write(enc)
print("inter_music.bin", len(enc), "bytes (stream", n, ")")
