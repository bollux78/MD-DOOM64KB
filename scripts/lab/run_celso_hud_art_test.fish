#!/usr/bin/env fish
# One-ROM test: original MegalDoom HUD graphics mapped onto ORIGINAL 56-color CRAM.
# No alternative renderer/DMA, no world-palette remapping, no SRAM.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/celso-hud-art
mkdir -p "$dest"; or exit 1

set -gx DOOM_TIMEDEMO 1
set -gx DOOM_NO_VSYNC 1
set -gx DOOM_FAST_DIVU 1
set -gx DOOM_CELL_LUT 1
set -gx DOOM_CACHE_SLOTS 16
set -gx DOOM_CACHE_STATS 0
set -gx DOOM_CLASSIC_TEXT_HUD 1
set -gx DOOM_HUD_DMA_STATUS_ONLY 1
set -gx DOOM_HUD_DMA24 0
set -gx DOOM_HUD_DMA24_NOHUDWRITE 0
set -gx DOOM_HUD_DOOMSTYLE_TEST 1
set -gx DOOM_HUD_WAD_ATLAS 1
set -gx DOOM_HUD_CELSO_ART 1
set -gx DOOM_HUD_CELSO_PALETTES 0
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_WALL_TAN_LUT 0
set -gx DOOM_WALLCOL_ASM 0
set -gx DOOM_BUILD_ID doom-md-celsoart-perf

set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
echo "Building $DOOM_BUILD_ID: genuine Celso art, ORIGINAL 56 world colors"
fish scripts/build_silent.fish > "$logfile" 2>&1
if test $status -ne 0
    echo "BUILD FAILED. Last 80 log lines:"
    tail -n 80 "$logfile"
    exit 1
end

set -l flags (string match -r '^BUILD_FLAGS:.*' < "$logfile")
if test (count $flags) -ne 1
    echo "ERROR: cannot verify unique BUILD_FLAGS"
    exit 1
end
for required in '-DDOOM_HUD_CELSO_ART' '-DDOOM_HUD_WAD_ATLAS' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CELL_LUT' '-DDOOM_CACHE_SLOTS=16' '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24'
    if not string match -q "*$required*" "$flags"
        echo "ERROR: missing compile flag: $required"
        exit 1
    end
end
for forbidden in '-DDOOM_HUD_CELSO_PALETTES' '-DDOOM_HUD_DMA24 ' '-DDOOM_WALLCOL_ASM' '-DDOOM_WALL_TAN_LUT'
    if string match -q "*$forbidden*" "$flags"
        echo "ERROR: incompatible experimental macro: $forbidden"
        exit 1
    end
end

if not test -s out/rom.bin; or not test -s out/release/rom.out
    echo 'ERROR: missing ROM/ELF'
    exit 1
end
python3 -c 'from pathlib import Path
import re
source=Path("src/gen_pal.h").read_text()
m=re.search(r"static const uint8_t genpal_cell\[256\]\s*=\s*\{([^}]+)\}",source,re.S)
assert m, "Missing source->cell palette table"
p=[int(v) for v in re.findall(r"\d+",m.group(1))]
assert len(p)==256
assert min(p)>=0 and max(p)<56, "Original 56-color palette corrupted"
assert any(v<14 for v in p) and any(v>=42 for v in p), "World palette restricted: abort"
tiles=Path("src/doom_wad_hud_tiles.h").read_text()
assert "#define DOOM_WAD_HUD_TOTAL_TILES 211" in tiles
assert "#define DOOM_WAD_HUD_KEY_OFFSET 208" in tiles
assert "doom_wad_hud_words[211][8]" in tiles
b=Path("out/rom.bin").read_bytes()
name="doom-md-celsoart-perf"
assert b[0x120:0x150].decode("ascii").strip()==name
assert b[0x150:0x180].decode("ascii").strip()==name
assert len(b)<=4*1024*1024
print("VERIFIED",name,len(b),"bytes | 56 world color slots retained, 211 genuine HUD tiles")
'; or exit 1

cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
if test -s out/release/symbol.txt
    cp out/release/symbol.txt "$dest/$DOOM_BUILD_ID.symbols.txt"; or exit 1
end
echo ""
echo "READY: $dest/$DOOM_BUILD_ID.bin"
echo "Check WORLD COLORS first (must match old 9.29 FPS ROM)."
echo "Then check genuine STBAR, neutral face, 16px red numbers and actual key icons."
echo "Finish DEMO3 (2134 frames) if visually stable. Screenshot during gameplay, please."
