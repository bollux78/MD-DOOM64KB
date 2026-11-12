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

# Preserve the fixed-width title fields in the SDK's header.
python3 - "$GDK/src/boot/rom_head.c" "$GDK/makefile.gen" <<'PYTHON'
from pathlib import Path
import sys
template = Path(sys.argv[1]).read_text()
title = "SAMPLE PROGRAM".ljust(48)
if template.count(title) != 2:
    raise SystemExit("Could not identify SGDK's two ROM title fields")
makefile = Path(sys.argv[2]).read_text()
path = Path("src/rom_header.c" if "rom_header.bin" in makefile else "src/boot/rom_head.c")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(template.replace(title, "NEXUS N01".ljust(48)))
PYTHON
libgcc="$("${prefix}gcc" -m68000 -print-libgcc-file-name)"
make release GDK="$GDK" PREFIX="$prefix" JAVA=java EXTRA_FLAGS="-std=gnu11" LIBGCC="$libgcc -lgcc"
cp out/rom.bin out/nexus-n01.bin
python3 - <<'PY'
from pathlib import Path
rom = Path("out/nexus-n01.bin").read_bytes()
assert len(rom) > 512 and rom[0x100:0x104] == b"SEGA"
assert b"NEXUS N01" in rom[0x120:0x180]
pc = int.from_bytes(rom[4:8], "big")
assert 0x200 <= pc < len(rom) and pc % 2 == 0
PY
sha256sum out/nexus-n01.bin
