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
[[ "$map" =~ ^(E[0-9]+M[0-9]+|MAP[0-9]+|EPISODE)$ && "$name" =~ ^[a-zA-Z0-9' '._-]+$ ]] || exit 2
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
export PATH="$GDK/bin:$PATH"
export OPENBLAS_NUM_THREADS=1 DREAD_NPAL=1
mkdir -p "$stage/src" "$stage/res" "$out"
if [[ -n ${DREAD_COPY_SEGA_S:-} ]]; then mkdir -p "$stage/src/boot"; fi
cp "$source_dir"/src/* "$stage/src/"
# the custom header goes in src/ (as in the D01 CI); SGDK keeps its own boot/sega.s
if [[ -n ${DREAD_COPY_SEGA_S:-} ]]; then cp "$GDK/src/boot/sega.s" "$stage/src/boot/"; fi
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
pvs_flags=
if [[ ${DREAD_GAMEPLAY:-0} == 1 ]]; then pvs_flags=-DDREAD_OPEN_PVS; fi
render_flags="-DDREAD_NO_MUSIC -DSTART_MUSIC=0"
title_flags="-DDREAD_TEXT_TITLE"
if [[ "$map" == EPISODE ]]; then
    [[ -z "$geometry_flag" ]] || exit 2
    render_flags="-DDREAD_EPISODE"
    if [[ ${DREAD_COMBAT:-0} == 1 ]]; then render_flags+=" -DDREAD_COMBAT"; fi
    levels=()
    if [[ -n ${DREAD_PREPARED_MAPS:-} ]]; then
        for n in {1..9}; do
            if [[ ${DREAD_GAMEPLAY:-0} == 1 ]] && ! grep -q 'map_fx\[19\]' "$DREAD_PREPARED_MAPS/E1M$n/mapdata.c"; then
                echo "Prepared map E1M$n predates gameplay schema; regenerate with current conv.py" >&2; exit 1
            fi
            if [[ ${DREAD_GAMEPLAY:-0} == 1 ]] && ! grep -q DREAD_OPEN_PVS "$DREAD_PREPARED_MAPS/E1M$n/pvs.c"; then
                echo "Prepared PVS E1M$n lacks open-world visibility; regenerate with -DDREAD_OPEN_PVS" >&2; exit 1
            fi
            levels+=("$DREAD_PREPARED_MAPS/E1M$n")
        done
    else
        palette="$stage/palette.json"
        mkdir -p "$stage/palette"
        if [[ ${DREAD_GAMEPLAY:-0} == 1 ]]; then
            cp "$source_dir/tools/gameplay_palette.json" "$palette"
        else
        # one palette for the whole episode: colour samples of every map (walls, flats, sky, sprites), one fit
        samples=()
        for n in {1..9}; do
            python3 "$source_dir/tools/conv.py" "$wad" "E1M$n" "$stage/palette" --row-only --collect-items "$stage/palette/E1M$n.npz" > /dev/null
            samples+=("$stage/palette/E1M$n.npz")
        done
        python3 "$source_dir/tools/conv.py" "$wad" E1M1 "$stage/palette" --row-only --fit-from "${samples[@]}" --palette-out "$palette"
        fi
        for n in {1..9}; do
            level="$stage/E1M$n"
            if [[ ${DREAD_SSF:-0} == 1 ]]; then
                DREAD_PAL_ROUNDS=1 python3 "$source_dir/tools/conv.py" "$wad" "E1M$n" "$level" --row-only --tex-pad 32
            else
                python3 "$source_dir/tools/conv.py" "$wad" "E1M$n" "$level" --row-only --tex-pad 32 --palette "$palette"
            fi
            cc -O2 -DPVS_GEN $pvs_flags -DDREAD_ROW_ONLY -I"$level" -I"$stage/src" -o "$level/pvsgen" \
               "$source_dir/tools/pvsgen.c" "$stage/src/render.c" "$level/mapdata.c"
            "$level/pvsgen" "$level/pvs.c"
            levels+=("$level")
        done
    fi
    if [[ ${DREAD_SSF:-0} == 1 ]]; then
        python3 "$source_dir/tools/pack_ssf.py" "$stage/src" "${levels[@]}"
        render_flags+=" -DDREAD_SSF"
    else
        python3 "$source_dir/tools/pack_episode.py" "$stage/src" "${levels[@]}"
    fi
    python3 "$source_dir/tools/gen_music.py" "$stage/res" --episode
    python3 "$source_dir/tools/gen_title.py" "$stage/src/title.c" --menu
    title_flags=
else
    python3 "$source_dir/tools/conv.py" "$wad" "$map" "$stage/src" "${convert_flags[@]}"
    cc -O2 -DPVS_GEN $pvs_flags -DDREAD_ROW_ONLY -I"$stage/src" -o "$stage/pvsgen" \
       "$source_dir/tools/pvsgen.c" "$stage/src/render.c" "$stage/src/mapdata.c"
    "$stage/pvsgen" "$stage/src/pvs.c"
fi
if [[ -z "$geometry_flag" ]]; then
    python3 "$source_dir/tools/gen_hud.py" --wad "$wad" --out "$stage/src/hud_assets.h"
    if [[ ${DREAD_GAMEPLAY:-0} == 1 ]]; then python3 "$source_dir/tools/gen_hud_white.py" "$stage/src/hud_assets.h"; fi
    sed -i 's|#include <stdint.h>|#include "mapdata.h"|' "$stage/src/hud_assets.h"
    python3 "$source_dir/tools/gen_weapon.py" "$wad" "$stage/src/weapon.c"
    if [[ "$map" == EPISODE ]]; then
        python3 "$source_dir/tools/pack_tiles.py" "$stage/src/hud_assets.h" "$stage/src/weapon.c" "$stage/src/image_tiles.h"
    fi
fi
if [[ ${DREAD_GAMEPLAY:-0} == 1 ]]; then
    # C7: gen_gameplay_assets.py restores the original Doom WAD weapon frames
    # used in C5. Do NOT overwrite weapon.c with the C6 custom sheet.
    python3 "$source_dir/tools/gen_gameplay_assets.py" "$wad" "$stage/src"
    python3 "$source_dir/tools/gen_ending.py" "$wad" "$stage/src"
    render_flags+=" -DDREAD_GAMEPLAY"
fi
python3 "$source_dir/tools/gen_scalers.py" "$stage/src/scalers.s"
gen_c="$stage/src/episode.c"; [[ -f "$gen_c" ]] || gen_c="$stage/src/mapdata.c"
if [[ ${DREAD_SSF:-0} != 1 ]]; then python3 "$source_dir/tools/gen_sky.py" "$source_dir/tools/sky_e1doom_256x72_pal.png" "$gen_c" "$stage/src/sky.c"; fi
python3 "$source_dir/tools/gen_tables.py" "$stage/src/tables.c"
sed 's/-flto -flto=auto -ffat-lto-objects/-fno-lto/g' "$GDK/makefile.gen" > "$stage/makefile.gen"
# toolchain: PREFIX=m68k-elf- from PATH, or DREAD_TC=/path/m68k-elf- (e.g. the CI runner's marsdev toolchain)
tc=${DREAD_TC:-m68k-elf-}
mk=(GDK="$GDK" OS=Linux PREFIX="$tc" CC="${tc}gcc" LD="${tc}ld" AR="${tc}ar" NM="${tc}nm" OBJCPY="${tc}objcopy" JAVA=java)
if [[ "$map" == EPISODE ]]; then
    make -C "$stage" -f makefile.gen "${mk[@]}" out/res/music.o 2>/dev/null \
      || make -C "$stage" -f makefile.gen "${mk[@]}" out/release/res/music.o 2>/dev/null || true
fi
make -C "$stage" -f makefile.gen -j3 release "${mk[@]}" \
    EXTRA_FLAGS="-ffreestanding -g -DNPAL=1 $geometry_flag $title_flags $render_flags ${DREAD_EXTRA_FLAGS:-} -DROM_NAME='\"$name\"' -DDREAD_MAP_LABEL='\"$map\"'" \
    LIBGCC="$(${tc}gcc -m68000 -print-libgcc-file-name) -lgcc"
rom="$stage/out/rom.bin"; [[ -f "$rom" ]] || rom="$stage/out/release/rom.bin"
elf="$stage/out/rom.out"; [[ -f "$elf" ]] || elf="$stage/out/release/rom.out"
if [[ ${DREAD_SSF:-0} == 1 ]]; then
    python3 "$source_dir/tools/finish_ssf.py" "$rom" "$stage/src/ssf-layout.json"
    cp "$stage/src/ssf-layout.json" "$out/ssf-layout.json"
fi
size=$(stat -c %s "$rom")
if [[ ${DREAD_SSF:-0} != 1 ]] && (( size > 4194304 )); then
    echo "$map excede 4 MiB: $size bytes" >&2
    exit 1
fi
cp "$rom" "$out/$map.bin"
cp "$elf" "$out/$map.elf"
