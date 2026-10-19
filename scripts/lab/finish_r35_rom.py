#!/usr/bin/env python3
"""Produce a trimmed LINEAR ROM, padded only to a 128KiB boundary. Reject overflows.
Do not change Doom, the existing optimized XGM2, or PCM bytes.
"""
from pathlib import Path
import argparse, hashlib, json, struct

p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('target',type=Path)
a=p.parse_args()
cap=4*1024*1024
source=a.source.read_bytes()
if not 0x200<len(source)<=cap:
    raise SystemExit(f'R35 REFUSED: payload {len(source)} B exceeds the 4MiB limit or is invalid')
if source[0x100:0x110] != b'SEGA MEGA DRIVE ':
    raise SystemExit(f'R35 REFUSED: expected linear SEGA MEGA DRIVE header, found {source[0x100:0x110]!r}')
if tuple(struct.unpack_from('>II',source,0x1A0))!=(0,cap-1):
    raise SystemExit('R35 REFUSED: header does not declare 0x000000-0x3FFFFF')
rom=bytearray(source)
size=((len(rom)+0x1FFFF)//0x20000)*0x20000
if size>cap: raise SystemExit('ROM size exceeds 4 MiB')
rom.extend(b'\xFF'*(size-len(rom)))
# Update header to the ACTUAL file size; never advertise nonexistent ROM.
struct.pack_into('>II',rom,0x1A0,0,size-1)
# Checksum covers only the bytes shipped in this ROM.
check=sum(int.from_bytes(rom[i:i+2],'big') for i in range(0x200,size,2))&0xFFFF
struct.pack_into('>H',rom,0x18E,check)
a.target.parent.mkdir(parents=True,exist_ok=True)
a.target.write_bytes(rom)
report=dict(rom=a.target.name,raw_bin_bytes=len(source),padded_rom_bytes=size,
            free_before_padding=size-len(source),rom_end=f'0x{size-1:08X}',
            mapper='linear (no SSF)',sram='R31 original A130F1 switching',
            md_checksum=f'{check:04X}',sha256=hashlib.sha256(rom).hexdigest())
(a.target.parent/('layout-'+a.target.stem+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
