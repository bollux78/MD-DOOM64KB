#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
: "${DOOM1_WAD:?Set DOOM1_WAD to a local classic Doom WAD}"
export GDK="${GDK:-$HOME/mars/m68k-elf}"
export PATH="$GDK/bin:$PATH"
prefix="${PREFIX:-m68k-elf-}"
map="${1:-E1M1}"
scale="${2:-3x}"
variant="${3:-base}"
case "$variant" in
    base) variant_flags="" ;;
    uv) variant_flags="-DNX_UV_INCREMENTAL" ;;
    lut) variant_flags="-DNX_RECIP_LUT" ;;
    asm) variant_flags="-DNX_COLUMN_ASM" ;;
    all) variant_flags="-DNX_UV_INCREMENTAL -DNX_RECIP_LUT -DNX_COLUMN_ASM" ;;
    *) echo "Unsupported optimization variant: $variant" >&2; exit 2 ;;
esac
config="$scale-$variant"
case "$scale" in
    2x) viewport_flag="" ;;
    3x) viewport_flag="-DNX_WIDE" ;;
    *) echo "Unsupported viewport scale: $scale" >&2; exit 2 ;;
esac
case "$map" in E1M1|E1M2|E1M9) ;; *) echo "Unsupported map: $map" >&2; exit 2;; esac
mkdir -p "out/$map"
rm -f "out/$map/nexus-wall-$config-${map,,}.bin"
if [[ ! -f out/.render-config || "$(cat out/.render-config)" != "$config" ]]; then
    rm -f out/{src,release/src}/{main,nexus,map_data,wall_data}.o
fi
python3 tools/import_wad.py "$DOOM1_WAD" --maps "$map" --emit src/map_data.c --textures src/wall_data.c > "out/$map/map-audit.json"

if [[ "$variant" == lut || "$variant" == all ]]; then
    python3 tools/reciprocal.py src/wall_reciprocal.h
fi
libgcc="$("${prefix}gcc" -m68000 -print-libgcc-file-name)"
make release GDK="$GDK" PREFIX="$prefix" JAVA=java EXTRA_FLAGS="-std=gnu11 -ffreestanding -DNX_2X2 -DNX_WALLS $viewport_flag $variant_flags" LIBGCC="$libgcc -lgcc"
printf "%s\n" "$config" > out/.render-config
python3 - "$map" "$config" <<'PY'
from pathlib import Path
import sys

map_name, config = sys.argv[1:]
raw = Path("out/release/rom.bin")
if not raw.is_file():
    raw = Path("out/rom.bin")
rom = bytearray(raw.read_bytes())
assert len(rom) > 512 and rom[0x100:0x104] == b"SEGA"
pc = int.from_bytes(rom[4:8], "big")
assert 0x200 <= pc < len(rom) and pc % 2 == 0
# Both 48-byte title fields are outside the Mega Drive checksum range.
title = f"NEXUS WALL {config.upper()} {map_name}".encode().ljust(48)
rom[0x120:0x150] = title
rom[0x150:0x180] = title
Path(f"out/{map_name}/nexus-wall-{config}-{map_name.lower()}.bin").write_bytes(rom)
PY
sha256sum "out/$map/nexus-wall-$config-${map,,}.bin"
