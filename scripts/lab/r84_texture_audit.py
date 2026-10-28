#!/usr/bin/env python3
"""Read-only feasibility audit; mirrors R_ComposeColumn's LOW_DETAIL sampling.

Checks every byte of the 128-byte source window, including bytes beyond height.
Only fully assigned windows are safe to bake without changing stale-cache semantics.
No timing claims and no generated game assets.
"""
import argparse
import hashlib
import json
import struct
import ctypes
import subprocess
import tempfile
from pathlib import Path


def audit(path, reference=None, columns=None):
    b = Path(path).read_bytes()
    n = struct.unpack_from('>h', b, 4)[0]
    directory = struct.unpack_from('>I', b, 8)[0]
    lumps = []
    for i in range(n):
        off = directory + 16*i
        pos, size = struct.unpack_from('>IH', b, off)
        assert pos + size <= len(b)
        name = b[off+8:off+16].rstrip(b'\0').decode('ascii')
        lumps.append((name, b[pos:pos+size]))
    named = dict(lumps)
    t1, tp = named['TEXTURE1'], named['TEXTUREP']
    nt = struct.unpack_from('>I', t1)[0]
    rows, unique, safe_columns = [], set(), 0
    for ti in range(nt):
        nameoff = struct.unpack_from('>I', t1, 4+ti*4)[0]
        name = t1[nameoff:nameoff+8].rstrip(b'\0').decode('ascii')
        off = struct.unpack_from('>H', tp, ti*2)[0]
        mask, width, height, overlap, count = struct.unpack_from('>HhhBB', tp, off)
        if not overlap:
            continue
        assert 0 < height <= 128
        patches = [struct.unpack_from('>hhhh', tp, off+8+j*8) for j in range(count)]
        cols = sorted({(x & 0xfffc) & mask for x in range(65536)})
        holes, complete, uniq = 0, 0, set()
        for x in cols:
            pixels = [None]*128
            probes = [(ctypes.c_ubyte*128)(*([v]*128)) for v in (0x55, 0xaa)] if reference else []
            for ox, oy, pn, pw in patches:
                patch = lumps[pn][1]
                actual_width = struct.unpack_from('>h', patch)[0]
                if not ox <= x < ox+actual_width:
                    continue
                p = struct.unpack_from('>I', patch, 8+(x-ox)*4)[0]
                for probe in probes:
                    reference(patch[p:], probe, oy, height)
                while patch[p] != 255:
                    y, length = patch[p:p+2]
                    assert p+length+4 <= len(patch)
                    position = oy+y
                    # Reference clips destination but does not advance source
                    # when originy is negative. Preserve that exact behavior.
                    take = length
                    if position < 0:
                        take += position
                        position = 0
                    take = min(take, height-position)
                    if take > 0:
                        pixels[position:position+take] = patch[p+3:p+3+take]
                    p += length+4
            missing = pixels.count(None)
            for seed, probe in zip((0x55, 0xaa), probes):
                assert bytes(probe) == bytes(seed if v is None else v for v in pixels), (name, x)
            holes += missing
            if not missing:
                complete += 1
                uniq.add(bytes(pixels))
                if columns is not None: columns.append((ti,x,bytes(pixels)))
        safe_columns += complete
        unique.update(uniq)
        rows.append(dict(index=ti, name=name, width=width, height=height,
                         sampled_columns=len(cols), fully_defined_128=complete,
                         unassigned_bytes=holes, unique_complete_columns=len(uniq)))
    total = sum(x['sampled_columns'] for x in rows)
    return dict(wad_sha256=hashlib.sha256(b).hexdigest(), textures=nt,
                mode='LOW_DETAIL: (texcolumn & 0xfffc) & widthmask',
                composite_textures=len(rows), sampled_columns=total,
                safe_columns=safe_columns, raw_full_window_bytes=total*128,
                unique_safe_bytes=len(unique)*128,
                dense_pointer_table_bytes=total*4, rows=rows,
                c_reference_verified=bool(reference),
                limitation='Static coverage and size only; no runtime frequency or speed measured.')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--wad', default='scripts/doom64.wad')
    ap.add_argument('--verify-c', action='store_true', help='Compare against the actual C compositor with two initial buffer patterns')
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        reference = None
        if args.verify_c:
            source = Path('src/r_draw.c').read_text()
            start = source.index('static void R_DrawColumnInCache(')
            end = source.index('\n/*', start)
            body = source[start:end].replace('static void ', 'void ', 1)
            c = Path(tmp)/'reference.c'
            c.write_text('#include <stdint.h>\n#include <string.h>\n#define __far\n#define _fmemcpy memcpy\ntypedef uint8_t byte;\ntypedef struct {uint8_t topdelta,length;} column_t;\n'+body)
            so = Path(tmp)/'reference.so'
            subprocess.run(['cc','-shared','-fPIC','-O2',str(c),'-o',str(so)], check=True)
            lib = ctypes.CDLL(str(so))
            reference = lib.R_DrawColumnInCache
            reference.argtypes = [ctypes.c_char_p,ctypes.POINTER(ctypes.c_ubyte),ctypes.c_int16,ctypes.c_int16]
            reference.restype = None
        print(json.dumps(audit(args.wad, reference), indent=2))
