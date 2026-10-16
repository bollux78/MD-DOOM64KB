#!/usr/bin/env fish
# One-ROM visual stability test: graphic bars, same 38x24 viewport, 1 DMA.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/hud-graphic-test
mkdir -p "$dest"; or exit 1

# Export flags in the outer script scope: Fish's -lx inside if is NOT safe.
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
set -gx DOOM_HUD_GRAPHIC_TEST 1
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_BUILD_ID doom-md-hudgfx-perf

set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
echo "Building $DOOM_BUILD_ID: graphic bars, 24-row 3D, conditional DMA"
fish scripts/build_silent.fish > "$logfile" 2>&1
if test $status -ne 0
    echo "ERROR: compile failed; last 60 log lines:"
    tail -n 60 "$logfile"
    exit 1
end

# Verify actual reported compiler flags, not just environment values.
set -l flags (string match -r '^BUILD_FLAGS:.*' < "$logfile")
if test (count $flags) -ne 1
    echo "ERROR: cannot identify compiler feature flags."
    exit 1
end
for required in '-DDOOM_HUD_GRAPHIC_TEST' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CLASSIC_TEXT_HUD' '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CACHE_SLOTS=16'
    if not string match -q "*$required*" "$flags"
        echo "ERROR: feature flag missing: $required"
        exit 1
    end
end
if string match -q '*-DDOOM_HUD_DMA24 *' "$flags"
    echo "ERROR: conflicting old DMA24 mode was enabled."
    exit 1
end
if not test -s out/rom.bin; or not test -s out/release/rom.out
    echo "ERROR: missing generated ROM or ELF."
    exit 1
end

python3 -c 'from pathlib import Path
b=Path("out/rom.bin").read_bytes()
label="doom-md-hudgfx-perf"
assert b[0x120:0x150].decode("ascii").strip()==label
assert b[0x150:0x180].decode("ascii").strip()==label
print("Verified ROM:",label,"bytes:",len(b))
'; or exit 1

cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1

echo "DONE: $dest/$DOOM_BUILD_ID.bin"
echo "First visually inspect the 3 gauges in BlastEm."
echo "If screen black, glitch, or frozen, stop and send the screenshot."
echo "Otherwise await 2134 frames and compare against 9.39 FPS."
