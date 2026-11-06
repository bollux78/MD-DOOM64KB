"""Write the staged filename into both Mega Drive title fields."""
from pathlib import Path
import sys

TITLE_FIELDS = (0x120, 0x150)
TITLE_BYTES = 48
RESULT_COLUMNS = 40


def write_title(rom, filename):
    if len(rom) < 0x200 or rom[0x100:0x104] != b"SEGA":
        raise ValueError("invalid Mega Drive ROM header")
    title = filename.encode("ascii")
    if not 1 <= len(title) <= RESULT_COLUMNS or any(not 32 <= c <= 126 for c in title):
        raise ValueError(f"filename must fit the {RESULT_COLUMNS}-column benchmark title: {filename}")
    for start in TITLE_FIELDS:
        rom[start:start + TITLE_BYTES] = title.ljust(TITLE_BYTES, b" ")


if __name__ == "__main__":
    path = Path(sys.argv[1])
    rom = bytearray(path.read_bytes())
    write_title(rom, path.name)
    path.write_bytes(rom)
