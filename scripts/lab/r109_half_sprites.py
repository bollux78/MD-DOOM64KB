#!/usr/bin/env python3
"""R109 build step: halve the HEIGHT of every sprite patch (S_START..S_END) in the converted
big-endian WAD. Width, size/offset headers (world units) unchanged; half texel r = full row 2r.
usage: r109_half_sprites.py WAD [--report out.json]"""
import argparse, json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from r108_half_walls import read, half_patch


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('wad'); ap.add_argument('--report'); a = ap.parse_args()
    b = bytearray(Path(a.wad).read_bytes()); d, ents = read(b)
    names = [e[0].rstrip(b'\0').decode('latin1') for e in ents]
    ss, se = names.index('S_START'), names.index('S_END')
    out = bytearray(b); before = after = count = 0
    while len(out) & 3: out.append(0)
    for i in range(ss + 1, se):
        name, p, z = ents[i]
        if z == 0: continue
        new = half_patch(bytes(b[p:p + z]))
        before += z; after += len(new); count += 1
        ents[i][1] = len(out); ents[i][2] = len(new); out += new
        while len(out) & 3: out.append(0)
    dirpos = len(out)
    for e in ents: out += struct.pack('>IHH', e[1], e[2], 0) + e[0]
    struct.pack_into('>I', out, 8, dirpos)
    Path(a.wad).write_bytes(out)
    rep = dict(sprites=count, sprite_bytes_before=before, sprite_bytes_after=after)
    print('R109 half sprites:', json.dumps(rep))
    if a.report: Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')


if __name__ == '__main__':
    main()
