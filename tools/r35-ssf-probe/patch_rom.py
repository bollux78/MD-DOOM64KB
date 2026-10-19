#!/usr/bin/env python3
"""Create a 5 MiB SSF2 hardware probe from the SGDK mini-program.
Pad and install independent canary markers in ROM bank windows.
The resulting file contains no Doom code or data; it is a mapper diagnostic.
"""
from pathlib import Path
import argparse, hashlib, json, struct
p=argparse.ArgumentParser()
p.add_argument('input', type=Path)
p.add_argument('output', type=Path)
args=p.parse_args()
payload=args.input.read_bytes()
assert len(payload) < 0x7F000, ("Probe must fit in the fixed bank", len(payload))
size=5*1024*1024
rom=bytearray(b'\xFF'*size)
rom[:len(payload)]=payload
# System type selects SSF for emulators that honor it; actual EverDrive-MD
# v2 may select SSF2 by ROM size instead, so verify on physical hardware.
rom[0x100:0x110]=b'SEGA SSF        '
# Conventional Sega Genesis ROM range fields.
struct.pack_into('>II',rom,0x1A0,0,size-1)
# Declare odd-lane SRAM, matching Doom's established cartridge aperture.
rom[0x1B0:0x1B2]=b'RA'
struct.pack_into('>HII',rom,0x1B2,0xF820,0x00200000,0x0020FFFF)
# Distinct byte sentinels used by tools/r35-ssf-probe/main.c.
for offset,value in [
    (0x080000,0x11), (0x200001,0x22), (0x280001,0x33),
    (0x400000,0x88), (0x480000,0x99)
]:
    rom[offset]=value
# Sega checksum is 16-bit sum of big-endian words from 0x200 to ROM end.
checksum=sum((rom[i]<<8)+rom[i+1] for i in range(0x200,size,2))&0xFFFF
struct.pack_into('>H',rom,0x18E,checksum)
assert rom[0x100:0x110]==b'SEGA SSF        '
assert struct.unpack_from('>II',rom,0x1A0)==(0,size-1)
assert all(rom[k]==v for k,v in [(0x080000,0x11),(0x200001,0x22),
                                 (0x280001,0x33),(0x400000,0x88),
                                 (0x480000,0x99)])
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_bytes(rom)
record={"file":args.output.name,"size":size,"fixed_bank_payload":len(payload),
        "rom_end":"0x004FFFFF","ssf_header":True,
        "checksum":f"{checksum:04X}",
        "sha256":hashlib.sha256(rom).hexdigest()}
(args.output.parent/'probe-report.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
