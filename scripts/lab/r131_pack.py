#!/usr/bin/env python3
"""R131: pack synthetic 512KiB bank markers into an SGDK-built test ROM.
No WAD/assets/credentials. Output is private by default.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

PAGE = 512 * 1024


def signature(p):
    return (0xA1310000 ^ (p * 0x10203) ^ (p << 24)) & 0xFFFFFFFF


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', type=Path, required=True, help='SGDK executable ROM (<512KiB)')
    ap.add_argument('--pages', type=int, choices=(8, 10, 16, 24, 30), required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    rom = a.base.read_bytes()
    if not (0x200 <= len(rom) < PAGE):
        ap.error('base ROM must fit entirely in fixed 512KiB page 0')
    if rom[:8] == bytes(8):
        ap.error('missing vector table')
    result = bytearray(a.pages * PAGE)
    result[:len(rom)] = rom
    result[0x100:0x110] = (b'SEGA SSF' if a.pages > 8 else b'SEGA MEGA DRIVE').ljust(16, b' ')
    result[0x1A0:0x1A8] = struct.pack('>II', 0, 4 * 1024 * 1024 - 1)
    for page in range(1, a.pages):
        struct.pack_into('>I', result, page * PAGE + 0x100, signature(page))
    checksum = sum((hi << 8) | lo for hi, lo in zip(result[0x200::2], result[0x201::2])) & 0xFFFF
    struct.pack_into('>H', result, 0x18E, checksum)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(result)
    verify = a.out.read_bytes()
    assert len(verify) == a.pages * PAGE
    assert all(struct.unpack_from('>I', verify, p * PAGE + 0x100)[0] == signature(p)
               for p in range(1, a.pages))
    print(json.dumps({
        'rom': a.out.name, 'bytes': len(verify), 'pages': a.pages,
        'sha256': hashlib.sha256(verify).hexdigest(),
        'header': verify[0x100:0x110].decode('ascii').strip()
    }, indent=2))


if __name__ == '__main__':
    main()
