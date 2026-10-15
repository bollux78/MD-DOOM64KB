#!/usr/bin/env fish
# One ROM: single DMA per frame, 24 rows normally or 28 when HUD changes.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/hud-single-dma
mkdir -p "$dest"; or exit 1

# All flags must survive Fish block scope and reach child build process.
set -gx DOOM_TIMEDEMO 1
set -gx DOOM_NO_VSYNC 1
set -gx DOOM_FAST_DIVU 1
set -gx DOOM_CELL_LUT 1
set -gx DOOM_CACHE_SLOTS 16
set -gx DOOM_CACHE_STATS 0
set -gx DOOM_CLASSIC_TEXT_HUD 1
set -gx DOOM_HUD_DMA24 0
set -gx DOOM_HUD_DMA24_NOHUDWRITE 0
set -gx DOOM_HUD_SINGLE_DMA 1
set -gx DOOM_BUILD_ID doom-md-singledma-perf

echo "Building $DOOM_BUILD_ID"
fish scripts/build_silent.fish > "$dest/build-$DOOM_BUILD_ID.log" 2>&1
if test $status -ne 0
    echo "Compiler failed. Last 50 lines:"
    tail -n 50 "$dest/build-$DOOM_BUILD_ID.log"
    exit 1
end
for flag in '-DDOOM_HUD_SINGLE_DMA' '-DDOOM_CLASSIC_TEXT_HUD'
    if not grep -q -- "$flag" "$dest/build-$DOOM_BUILD_ID.log"
        echo "ERROR: missing required build flag $flag"
        exit 1
    end
end
if grep -q -- '-DDOOM_HUD_DMA24 ' "$dest/build-$DOOM_BUILD_ID.log"
    echo "ERROR: old DMA24 flag also enabled"
    exit 1
end
if not test -s out/rom.bin
    echo "ERROR: ROM file missing"
    exit 1
end
python3 -c 'import pathlib
b=pathlib.Path("out/rom.bin").read_bytes()
s="doom-md-singledma-perf"
assert b[0x120:0x150].decode("ascii").strip()==s
assert b[0x150:0x180].decode("ascii").strip()==s
print("Verified ROM identity:",s)
'; or exit 1
cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
echo "READY: $dest/$DOOM_BUILD_ID.bin"
echo "Test in BlastEm first; do not replace any known-stable ROM."
