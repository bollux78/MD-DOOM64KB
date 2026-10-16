#!/usr/bin/env fish
# Doom-inspired static metallic 32px HUD. One experimental PERF ROM only.
# Graphics: a boot-uploaded 32x32 portrait and four 8x8 border tiles,
# dynamic current ammo, health, armor, weapon and keycards.
# The tested 24/28 conditional single-DMA design stays unchanged.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/doomstyle-hud
mkdir -p "$dest"; or exit 1

# Fish export: use global/exported scope to survive conditional blocks.
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
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_BUILD_ID doom-md-doomhud-perf

set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
echo "Building $DOOM_BUILD_ID (Doom-style HUD, status-only DMA)"
fish scripts/build_silent.fish > "$logfile" 2>&1
if test $status -ne 0
    echo "ERROR: compilation failed, last 70 lines:"
    tail -n 70 "$logfile"
    exit 1
end

set -l flags (string match -r '^BUILD_FLAGS:.*' < "$logfile")
if test (count $flags) -ne 1
    echo "ERROR: missing unique BUILD_FLAGS line"
    exit 1
end
for required in '-DDOOM_HUD_DOOMSTYLE_TEST' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CLASSIC_TEXT_HUD' '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CACHE_SLOTS=16'
    if not string match -q "*$required*" "$flags"
        echo "ERROR: missing compiler switch $required"
        exit 1
    end
end
if string match -q '*-DDOOM_HUD_DMA24 ' "$flags"
    echo 'ERROR: unsupported secondary DMA24 mode enabled'
    exit 1
end
if not test -s out/rom.bin; or not test -s out/release/rom.out
    echo 'ERROR: ROM or ELF missing'
    exit 1
end

python3 -c 'from pathlib import Path
b=Path("out/rom.bin").read_bytes()
name="doom-md-doomhud-perf"
assert b[0x120:0x150].decode("ascii").strip()==name
assert b[0x150:0x180].decode("ascii").strip()==name
assert len(b) <= 4 * 1024 * 1024
print("Verified ROM:",name,"size:",len(b),"bytes")
'; or exit 1

cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
if test -f out/release/symbol.txt
    cp out/release/symbol.txt "$dest/$DOOM_BUILD_ID.symbols.txt"; or exit 1
end

echo ""
echo "DONE: $dest/$DOOM_BUILD_ID.bin"
echo "Test in BlastEm, check metallic bar and fixed face, then 2134 DEMO3 frames."
echo "Known-good source and Fullscreen are untouched."
