#!/usr/bin/env python3
"""Advertise Sega CD compatibility in the cartridge's device support field."""
from pathlib import Path
import sys

source, target = map(Path, sys.argv[1:])
rom = bytearray(source.read_bytes())
assert len(rom) >= 0x200 and rom[0x100:0x104] == b"SEGA", "invalid cartridge ROM"
field = bytes(rom[0x190:0x1A0]).rstrip(b" ")
assert b"J" in field and len(field) < 16, ("unexpected device support field", field)
if b"C" not in field:
    field += b"C"
rom[0x190:0x1A0] = field.ljust(16, b" ")
target.write_bytes(rom)
print(f"Mode 1 ROM: {target} ({len(rom)} bytes; devices {field.decode('ascii')})")
