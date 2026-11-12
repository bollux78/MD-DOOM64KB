#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
: "${DOOM1_WAD:?Set DOOM1_WAD to a local classic Doom WAD}"
export GDK="${GDK:-$HOME/mars/m68k-elf}"
export PATH="$GDK/bin:$PATH"
prefix="${PREFIX:-m68k-elf-}"
mkdir -p out
rm -f out/nexus-n01.bin
python3 tools/import_wad.py "$DOOM1_WAD" --emit src/map_data.c > out/map-audit.json
cat out/map-audit.json

libgcc="$("${prefix}gcc" -m68000 -print-libgcc-file-name)"
make release GDK="$GDK" PREFIX="$prefix" JAVA=java EXTRA_FLAGS="-std=gnu11 -ffreestanding" LIBGCC="$libgcc -lgcc"
python3 - <<'PY'
from pathlib import Path
raw = Path("out/release/rom.bin")
if not raw.is_file():
    raw = Path("out/rom.bin")
rom = bytearray(raw.read_bytes())
assert len(rom) > 512 and rom[0x100:0x104] == b"SEGA"
pc = int.from_bytes(rom[4:8], "big")
assert 0x200 <= pc < len(rom) and pc % 2 == 0
# Both 48-byte title fields are outside the Mega Drive checksum range.
title = b"NEXUS N01".ljust(48)
rom[0x120:0x150] = title
rom[0x150:0x180] = title
Path("out/nexus-n01.bin").write_bytes(rom)
PY
sha256sum out/nexus-n01.bin
