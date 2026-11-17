#!/usr/bin/env bash
# Assemble and build the R128 All Shareware PLAY variant in a private copy.
set -euo pipefail

if [[ $# != 3 ]]; then
    echo "Usage: bash scripts/lab/build_r128_shareware.sh DOOM1.WAD SGDK_DIR NEW_OUTPUT_DIR" >&2
    exit 2
fi

shareware="$(realpath "$1")"
gdk="$(realpath "$2")"
output="$(realpath -m "$3")"
root="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
revision="$(git -C "$root" rev-parse HEAD)"
for tool in fish python3 patch java make cc xz; do command -v "$tool" >/dev/null; done
test -x "$gdk/bin/m68k-elf-gcc"
test -f "$gdk/lib/libmd.a"
test "$(sha256sum "$shareware" | cut -d ' ' -f 1)" = 1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771
mkdir -p "$(dirname "$output")"
mkdir "$output"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
source="$scratch/source"
mkdir "$source"
git -C "$root" archive "$revision" | tar -x -C "$source"
cd "$source"

export PYTHONDONTWRITEBYTECODE=1
export PATH="$gdk/bin:$PATH"
export DOOM_MD_GDK="$gdk"
export DOOM_R20_BGM_VGM="$source/res/e1m1.vgm"
export R128_EPISODE_WAD="$scratch/shareware-e1.wad"
export HUD_WORK="$scratch/variants"
export MAKEFLAGS=-j1
export HUD_BSS_SLACK=128
lab=scripts/lab/r128-shareware

python3 scripts/lab/convert_r128_shareware_e1.py "$shareware" --out "$R128_EPISODE_WAD" > "$output/shareware-e1.json"
cp "$shareware" scripts/doom1.wad
xz -dc assets/r18-e1m1.vgm.xz > res/e1m1.vgm
mkdir -p dist/hud
python3 scripts/lab/gen_r81_font.py --wad scripts/doom1.wad --out src/r81_menu_font.h --preview dist/hud/font-preview.png
python3 scripts/lab/gen_r22_pixel4.py
python3 scripts/lab/gen_r49_colormix.py
python3 scripts/lab/gen_hud_wad.py --wad scripts/doom1.wad --out src/hud_wad_assets.h --preview dist/hud/hud-preview.png

bash "$lab/apply-base.sh"
for overlay in "$lab"/[0-9][0-9]-*.patch; do
    patch -p1 --batch --fuzz=0 < "$overlay"
done
if [[ "${R128_BG_DMA:-0}" == 1 && "${R128_BG_PROBE:-0}" == 1 ]]; then
    echo "Select either the BG diagnostic or the DMA experiment" >&2
    exit 2
fi
if [[ "${R128_BG_DMA:-0}" == 1 ]]; then
    python3 "$lab/install_pairv_dma.py"
fi
if [[ "${R128_BG_PROBE:-0}" == 1 ]]; then
    # Allow the probe's row signatures and counters in this diagnostic ROM.
    export HUD_BSS_SLACK=240
    python3 "$lab/install_pairv_probe.py"
fi
if [[ "${R128_E1M1_MENU_BENCH:-0}" == 1 ]]; then
    python3 "$lab/install_e1m1_menu_bench.py"
fi
if [[ -n "${R128_RAW_BG:-}" ]]; then
    if [[ "${R128_E1M1_MENU_BENCH:-0}" != 1 || "${R128_BG_DMA:-0}" == 1 || "${R128_BG_PROBE:-0}" == 1 ]]; then
        echo "Raw BG requires the E1M1 menu benchmark and its own DMA path" >&2
        exit 2
    fi
    python3 "$lab/install_raw_bg.py" "$R128_RAW_BG"
fi
if [[ "${R128_PIXEL4_PLAY:-0}" == 1 ]]; then
    if [[ -n "${R128_RAW_BG:-}" || "${R128_BG_DMA:-0}" == 1 || "${R128_BG_PROBE:-0}" == 1 ]]; then
        echo "Pixel4 play uses its own tile uploader" >&2
        exit 2
    fi
    cp "$lab/pixel4-play.inc" src/r128_pixel4_play.inc
    python3 "$lab/install_pixel4_cache.py"
fi
if [[ "${R128_SGDK211_COMPAT:-0}" == 1 ]]; then
    cp "$lab/sgdk211_memcmp.c" src/r128_sgdk_memcmp.c
fi
fish -n scripts/lab/build_r35_linear.fish
python3 scripts/lab/build_r71a12mul_hud.py 2>&1 | tee "$output/build.log"
cp -a dist/hud/. "$output/"
elf="$(find "$output" -maxdepth 1 -name '*.elf' -print -quit)"
M68K_NM="$gdk/bin/m68k-elf-nm" python3 scripts/lab/r122_z80_layout.py "$elf" --require | tee "$output/audio-layout.txt"
printf '%s\n' "$revision" > "$output/SOURCE-COMMIT"
sha256sum "$shareware" "$R128_EPISODE_WAD" > "$output/BUILD-INPUTS.sha256"
