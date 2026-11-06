"""Create five private ROMs from the same linked executable."""
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rom_identity import write_title

rom_path, elf, out = map(Path, sys.argv[1:])
nm = Path.home() / "mars/m68k-elf/bin/m68k-elf-nm"
symbols = subprocess.check_output([nm, elf], text=True).splitlines()
address, = [int(line.split()[0], 16) for line in symbols
            if line.endswith(" scd_logic_mode")]
rom = bytearray(rom_path.read_bytes())
assert 0x200 <= address < len(rom) and rom[address] == 0xA0
field = rom[0x190:0x1A0].rstrip(b" ")
assert b"J" in field and len(field) < 16
rom[0x190:0x1A0] = (field if b"C" in field else field + b"C").ljust(16, b" ")
out.mkdir(parents=True, exist_ok=True)
for label, mask in (("native", 0), ("sight", 1), ("sound", 2), ("rays", 4), ("all", 7)):
    rom[address] = 0xA0 | mask
    checksum = sum(word for word, in struct.iter_unpack(">H", memoryview(rom)[0x200:]))
    rom[0x18E:0x190] = struct.pack(">H", checksum & 0xFFFF)
    target = out / f"doom-md-scd-logic-{label}.bin"
    write_title(rom, target.name)
    target.write_bytes(rom)
    print(target)
