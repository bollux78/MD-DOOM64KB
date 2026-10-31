#!/usr/bin/env python3
"""R108 build step: halve the HEIGHT of every wall patch (P_START..P_END) in the big-endian
Doom64KB WAD, and regenerate src/r84_columns.h for half-height composed columns.

Width is untouched (the inherited conversion already stores walls at 1/4 width). Texture
definitions (TEXTURE1/TEXTUREP: width, height, origins) stay in world units; the renderer
samples at half rate (R108 kernel: phase/step >> 1, row mask 63) and composes with
originy >> 1. Half texel r = full row 2r. Sprites, HUD, menus, intermission: unchanged.

usage: r108_half_walls.py WAD --r84 src/r84_columns.h [--report out.json]
"""
import argparse, json, struct
from pathlib import Path


def read(b):
    n = struct.unpack_from('>h', b, 4)[0]; d = struct.unpack_from('>I', b, 8)[0]
    ents = []
    for i in range(n):
        o = d + 16 * i
        p, z = struct.unpack_from('>IH', b, o)
        ents.append([b[o + 8:o + 16], p, z])
    return d, ents


def decode_column(b, q):
    rows = {}
    while b[q] != 0xFF:
        td, ln = b[q], b[q + 1]
        for k in range(ln): rows[td + k] = b[q + 3 + k]
        q += ln + 4
    return rows


def encode_column(rows):
    out = bytearray(); keys = sorted(rows); i = 0
    while i < len(keys):
        j = i
        while j + 1 < len(keys) and keys[j + 1] == keys[j] + 1 and keys[j + 1] - keys[i] < 254: j += 1
        start = keys[i]; data = bytes(rows[k] for k in keys[i:j + 1])
        assert start < 255 and len(data) < 256
        out += bytes([start, len(data), data[0]]) + data + bytes([data[-1]])
        i = j + 1
    return bytes(out + b'\xff')


def half_patch(lump):
    w, h, lo, to = struct.unpack_from('>hhhh', lump)
    offs = struct.unpack_from('>%dI' % w, lump, 8)
    cache = {}; body = bytearray(); new_offs = []
    base = 8 + 4 * w
    for c in offs:
        if c not in cache:
            full = decode_column(lump, c)
            half = {r // 2: v for r, v in full.items() if r % 2 == 0}
            enc = encode_column(half)
            cache[c] = base + len(body); body += enc
        new_offs.append(cache[c])
    out = struct.pack('>hhhh', w, h, lo, to) + struct.pack('>%dI' % w, *new_offs) + bytes(body)
    while len(out) & 3: out += b'\0'
    return out


def compose_half(lumps, tp, ti):
    """Mirror of R_ComposeColumn + R_DrawColumnInCache with (originy>>1, (height+1)>>1)."""
    off = struct.unpack_from('>H', tp, ti * 2)[0]
    mask, width, height, overlap, count = struct.unpack_from('>HhhBB', tp, off)
    if not overlap: return {}
    hh = (height + 1) >> 1
    patches = [struct.unpack_from('>hhhh', tp, off + 8 + j * 8) for j in range(count)]
    cols = {}
    for x in sorted({(x & 0xfffc) & mask for x in range(65536)}):
        pix = [None] * 64
        for ox, oy, pn, pw in patches:
            patch = lumps[pn]; aw = struct.unpack_from('>h', patch)[0]
            if not ox <= x < ox + aw: continue
            q = struct.unpack_from('>I', patch, 8 + (x - ox) * 4)[0]
            while patch[q] != 255:
                y, ln = patch[q], patch[q + 1]
                pos = (oy >> 1) + y; take = ln
                if pos < 0: take += pos; pos = 0          # source not advanced (reference quirk)
                take = min(take, hh - pos)
                for k in range(max(0, take)):
                    if pos + k < 64: pix[pos + k] = patch[q + 3 + k]
                q += ln + 4
        if None not in pix: cols[x] = bytes(pix)
    return cols


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('wad'); ap.add_argument('--r84', required=True); ap.add_argument('--report')
    a = ap.parse_args()
    b = bytearray(Path(a.wad).read_bytes()); d, ents = read(b)
    names = [e[0].rstrip(b'\0').decode('latin1') for e in ents]
    ps, pe = names.index('P_START'), names.index('P_END')
    before = after = 0; count = 0
    tail = bytearray()
    for i in range(ps + 1, pe):
        name, p, z = ents[i]
        if z == 0: continue
        new = half_patch(bytes(b[p:p + z]))
        before += z; after += len(new); count += 1
        ents[i][1] = None; ents[i].append(new)
    # Rebuild: all original bytes kept (lump data may follow the old directory), halved patches
    # appended, new directory at the end. repack_wad later drops the dead bytes.
    out = bytearray(b)
    while len(out) & 3: out.append(0)
    for e in ents:
        if e[1] is None:
            e[1] = len(out); e[2] = len(e[3]); out += e[3]
            while len(out) & 3: out.append(0)
    dirpos = len(out)
    for e in ents: out += struct.pack('>IHH', e[1], e[2], 0) + e[0]
    struct.pack_into('>I', out, 8, dirpos)
    Path(a.wad).write_bytes(out)
    # r84: half-height baked composites (64-byte entries; pool padded so 128-byte copies stay in bounds).
    lumps = [bytes(out[e[1]:e[1] + e[2]]) for e in ents]
    named = {n: l for n, l in zip(names, lumps)}
    tp = named['TEXTUREP']; nt = struct.unpack_from('>I', named['TEXTURE1'])[0]
    pool = bytearray(); dedup = {}; starts = []; entries = []; simple_starts = []; simple = []; patches = []
    for t in range(nt):
        off = struct.unpack_from('>H', tp, t * 2)[0]; mask, w, h, over, cnt = struct.unpack_from('>HhhBB', tp, off)
        cols = compose_half(lumps, tp, t)
        starts.append(len(entries))
        for x in range(0, mask + 1, 4):
            c = cols.get(x)
            if c is None: entries.append(0xffffffff); continue
            if c not in dedup: dedup[c] = len(pool); pool += c
            entries.append(dedup[c])
        simple_starts.append(len(simple)); pn = struct.unpack_from('>h', tp, off + 12)[0]
        patches.append(pn if cnt == 1 and not over else -1)
        if cnt == 1 and not over:
            patch = lumps[pn]; simple.extend(struct.unpack_from('>I', patch, 8 + x * 4)[0] + 3 for x in range(mask + 1))
    pool += bytes(64)
    def arr(typ, name, v): return 'static const ' + typ + ' ' + name + '[]={' + ','.join(str(x) + 'u' if x >= 0 else str(x) for x in v) + '};\n'
    txt = arr('uint8_t', 'r84_pixels', pool) + arr('uint32_t', 'r84_offsets', entries) + arr('uint16_t', 'r84_starts', starts)
    txt += arr('uint16_t', 'r84_simple_starts', simple_starts) + arr('int16_t', 'r84_patches', patches) + arr('uint32_t', 'r84_simple_offsets', simple)
    Path(a.r84).write_text(txt)
    rep = dict(patches=count, patch_bytes_before=before, patch_bytes_after=after, r84_pool_bytes=len(pool),
               r84_baked_entries=sum(1 for e in entries if e != 0xffffffff))
    print('R108 half walls:', json.dumps(rep))
    if a.report: Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')


if __name__ == '__main__':
    main()
