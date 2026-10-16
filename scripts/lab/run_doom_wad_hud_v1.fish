#!/usr/bin/env fish
# Doom HUD atlas V1: build just one experimental ROM for BlastEm.
# Based on the tested Doom-style HUD (9.26 FPS / 2134 DEMO3 frames).
# Keeps the 38x24 3D scene + 4 HUD rows and single conditional DMA.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/doom-hud-atlas
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
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_WALL_TAN_LUT 0
set -gx DOOM_WALLCOL_ASM 0
set -gx DOOM_BUILD_ID doom-md-wadhud-v1-perf

set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
echo "Building $DOOM_BUILD_ID"
fish scripts/build_silent.fish > "$logfile" 2>&1
if test $status -ne 0
    echo "ERROR: compilation or asset conversion failed. Last 70 lines:"
    tail -n 70 "$logfile"
    exit 1
end

set -l flags (string match -r '^BUILD_FLAGS:.*' < "$logfile")
if test (count $flags) -ne 1
    echo "ERROR: cannot verify compiler feature flags"
    tail -n 25 "$logfile"
    exit 1
end
for needed in '-DDOOM_HUD_WAD_ATLAS' '-DDOOM_HUD_DOOMSTYLE_TEST' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CELL_LUT' '-DDOOM_CACHE_SLOTS=16' '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24'
    if not string match -q "*$needed*" "$flags"
        echo "ERROR: missing compile flag $needed"
        exit 1
    end
end
for forbidden in '-DDOOM_HUD_DMA24 ' '-DDOOM_WALLCOL_ASM ' '-DDOOM_WALL_TAN_LUT '
    if string match -q "*$forbidden*" "$flags"
        echo "ERROR: forbidden experimental flag $forbidden"
        exit 1
    end
end

if not test -s src/doom_wad_hud_tiles.h
    echo "ERROR: generated tiles header missing"
    exit 1
end
if not test -s out/rom.bin; or not test -s out/release/rom.out
    echo "ERROR: missing ROM or ELF output"
    exit 1
end

python3 -c 'from pathlib import Path
b=Path("out/rom.bin").read_bytes()
name="doom-md-wadhud-v1-perf"
assert b[0x120:0x150].decode("ascii").strip()==name
assert b[0x150:0x180].decode("ascii").strip()==name
assert len(b)<=4*1024*1024
h=Path("src/doom_wad_hud_tiles.h").read_text()
assert "#define DOOM_WAD_HUD_TOTAL_TILES 188" in h
assert "#define DOOM_WAD_HUD_BG_TILES 152" in h
assert "doom_wad_hud_words[188][8]" in h
print("Verified 188 HUD tiles and ROM",name,len(b),"bytes")
'; or exit 1

cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
if test -s out/release/symbol.txt
    cp out/release/symbol.txt "$dest/$DOOM_BUILD_ID.symbols.txt"; or exit 1
end
string match -r '^Status graphics found.*|^Background:.*|^Portrait:.*|^Digits:.*|^Sources:.*|^Doom HUD tiles:.*' < "$logfile"
echo ""
echo "READY: $dest/$DOOM_BUILD_ID.bin"
echo "Inspect bar/face/red numerals first; then run DEMO3 to 2134 frames."
echo "If black screen, do not run on hardware; share the build log/screenshot."
