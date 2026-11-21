#!/usr/bin/env bash
set -euo pipefail
: "${GDK:?Set GDK to an absolute SGDK path}"
if [[ $# != 4 && ! ( $# == 5 && "$5" == --geometry-only ) ]]; then
    echo "Uso: $0 WAD MAPA DIRETORIO_SAIDA NOME [--geometry-only]" >&2
    exit 2
fi
source_dir=$(cd "$(dirname "$0")/.." && pwd)
wad=$(realpath "$1")
map=${2^^}
out=$(realpath -m "$3")
name=$4
[[ "$map" =~ ^(E[0-9]+M[0-9]+|MAP[0-9]+)$ && "$name" =~ ^[a-zA-Z0-9' '._-]+$ ]] || exit 2
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
export PATH="$GDK/bin:$PATH"
export OPENBLAS_NUM_THREADS=1 DREAD_NPAL=1
mkdir -p "$stage/src/boot" "$stage/res" "$out"
cp "$source_dir"/src/* "$stage/src/"
cp "$GDK/src/boot/sega.s" "$stage/src/boot/"
header="$GDK/src/boot/rom_header.c"
if [[ ! -f "$header" ]]; then header="$GDK/src/boot/rom_head.c"; fi
sed -E "s/\"[^\"]{48}\"/\"$(printf '%-48.48s' "$name")\"/g" "$header" > "$stage/src/rom_header.c"
convert_flags=(--row-only)
geometry_flag=
if [[ ${5:-} == --geometry-only ]]; then
    convert_flags+=(--geometry-only)
    geometry_flag=-DDREAD_GEOMETRY_ONLY
    rm "$stage/src/game_hud.c"
fi
python3 "$source_dir/tools/conv.py" "$wad" "$map" "$stage/src" "${convert_flags[@]}"
cc -O2 -DPVS_GEN -DDREAD_ROW_ONLY -I"$stage/src" -o "$stage/pvsgen" \
   "$source_dir/tools/pvsgen.c" "$stage/src/render.c" "$stage/src/mapdata.c"
"$stage/pvsgen" "$stage/src/pvs.c"
if [[ -z "$geometry_flag" ]]; then
    python3 "$source_dir/tools/gen_hud.py" --wad "$wad" --out "$stage/src/hud_assets.h"
    sed -i 's|#include <stdint.h>|#include "mapdata.h"|' "$stage/src/hud_assets.h"
    python3 "$source_dir/tools/gen_weapon.py" "$wad" "$stage/src/weapon.c"
fi
python3 "$source_dir/tools/gen_scalers.py" "$stage/src/scalers.s"
python3 "$source_dir/tools/gen_tables.py" "$stage/src/tables.c"
sed 's/-flto -flto=auto -ffat-lto-objects/-fno-lto/g' "$GDK/makefile.gen" > "$stage/makefile.gen"
make -C "$stage" -f makefile.gen -j3 release GDK="$GDK" PREFIX=m68k-elf- JAVA=java \
    EXTRA_FLAGS="-ffreestanding -g -DNPAL=1 -DDREAD_ROW_ONLY $geometry_flag -DDREAD_TEXT_TITLE -DDREAD_NO_MUSIC -DSTART_MUSIC=0 -DROM_NAME='\"$name\"' -DDREAD_MAP_LABEL='\"$map\"'" \
    LIBGCC="$(m68k-elf-gcc -m68000 -print-libgcc-file-name) -lgcc"
size=$(stat -c %s "$stage/out/rom.bin")
if (( size > 4194304 )); then
    echo "$map excede 4 MiB: $size bytes" >&2
    exit 1
fi
cp "$stage/out/rom.bin" "$out/$map.bin"
cp "$stage/out/rom.out" "$out/$map.elf"
