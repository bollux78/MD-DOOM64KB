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
export HUD_WORK="$output/prepared"
export MAKEFLAGS=-j1
export HUD_BSS_SLACK=384
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
if [[ "${R128_VERTICAL_DITHER:-0}" == 1 || "${R128_TONE_RESAMPLE:-0}" == 1 ]]; then
    # Each row uses the same stripe phase. Pair-V tile indices stay identical.
    python3 - <<'PYTHON'
from pathlib import Path
path = Path("src/r22_video.inc")
source = path.read_text()
checker = "(((x+row)&1u)==0u)"
assert source.count(checker) == 1
path.write_text(source.replace(checker, "((x&1u)==0u)").replace(
    "#if defined(DOOM_R73_R53_FIXED)\n    uint32_t result=0;",
    "#if defined(DOOM_R73_R53_FIXED)\n    (void)row;\n    uint32_t result=0;",
))
PYTHON
    export R128_VERTICAL_DITHER
fi
if [[ "${R128_SGDK211_COMPAT:-0}" == 1 ]]; then
    cp "$lab/sgdk211_memcmp.c" src/r128_sgdk_memcmp.c
fi
python3 "$lab/install_batches.py"
python3 - <<'PYHOOK'
from pathlib import Path
p=Path('scripts/lab/build_r35_linear.fish')
s=p.read_text()
anchor='    rm -rf out\n    rm -f res/music.rs res/music.d\n'
assert s.count(anchor)==1
s=s.replace(anchor,'    python3 scripts/lab/r128-shareware/map_format_lab.py; or exit 1\n'+anchor)
p.write_text(s)
PYHOOK
python3 "$lab/install_e1m1_menu_bench.py"
fish -n scripts/lab/build_r35_linear.fish
python3 scripts/lab/build_r71a12mul_hud.py 2>&1 | tee "$output/build.log"
cp -a dist/hud/. "$output/"
elf="$(find "$output" -maxdepth 1 -name '*.elf' -print -quit)"
M68K_NM="$gdk/bin/m68k-elf-nm" python3 scripts/lab/r122_z80_layout.py "$elf" --require | tee "$output/audio-layout.txt"
printf '%s\n' "$revision" > "$output/SOURCE-COMMIT"
sha256sum "$shareware" "$R128_EPISODE_WAD" > "$output/BUILD-INPUTS.sha256"
