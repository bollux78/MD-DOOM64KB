#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
: "${GDK:?Set GDK to SGDK}" "${DOOM1_WAD:?Set DOOM1_WAD to shareware Doom 1.9}"
export PATH="$GDK/bin:$PATH"
python3 tools/convert.py "$DOOM1_WAD" src
# The R128 SDK has a root-header rule; stock SGDK supplies its boot header.
if grep -Fq '$(SRC)/rom_header.c' "$GDK/makefile.gen"; then
    cp "$GDK/src/boot/rom_head.c" src/rom_header.c
else
    rm -f src/rom_header.c
fi
libgcc="$(m68k-elf-gcc -m68000 -print-libgcc-file-name)"
make release GDK="$GDK" PREFIX=m68k-elf- JAVA=java EXTRA_FLAGS='-std=gnu11 -ffreestanding -fno-strict-aliasing' LIBGCC="$libgcc -lgcc" -j2
python3 - <<'PY'
from pathlib import Path
p=Path('out/rom.bin')
if not p.exists():p=Path('out/release/rom.bin')
r=bytearray(p.read_bytes());title=b'NEODOOM P0 E1M1 PORTAL RAYS'.ljust(48)
r[0x120:0x150]=title;r[0x150:0x180]=title
Path('out/neodoom-p0-e1m1.bin').write_bytes(r)
PY
