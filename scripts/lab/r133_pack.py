#!/usr/bin/env python3
"""R133: 5MiB Doom + distinct page 8/9 signatures for its own boot test."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path


def sig(p):
    return (0xA1310000 ^ (p * 0x10203) ^ (p << 24)) & 0xFFFFFFFF


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--report',required=True,type=Path)
    a=ap.parse_args()
    subprocess.run([sys.executable,str(Path(__file__).with_name('r132_doom5m.py')),
                    '--input',str(a.input),'--output',str(a.output),
                    '--report',str(a.report)],check=True,stdout=subprocess.DEVNULL)
    b=bytearray(a.output.read_bytes())
    for p in (8,9):
        struct.pack_into('>I',b,p*512*1024+0x100,sig(p))
    checksum=sum((b[i]<<8)|b[i+1] for i in range(0x200,len(b),2))&0xffff
    struct.pack_into('>H',b,0x18e,checksum)
    a.output.write_bytes(b)
    report=json.loads(a.report.read_text())
    report.update(variant='r133-ssf2-5m-doom-selftest',sha256=hashlib.sha256(b).hexdigest(),
                  checksum=checksum,
                  page8_signature=hex(sig(8)),page9_signature=hex(sig(9)),
                  selftest='built-in startup: page8, page9, 1024 switches, bank 7 restore',
                  limitation='selftest shown before title; not SRAM/Z80/real cart validation')
    a.report.write_text(json.dumps(report,indent=2)+'\n')
    assert struct.unpack_from('>I',b,8*512*1024+0x100)[0]==sig(8)
    assert struct.unpack_from('>I',b,9*512*1024+0x100)[0]==sig(9)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
