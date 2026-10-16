#!/usr/bin/env fish
# Canonical HUD: 38x24 3D + four text-HUD rows.
# Reference: hudstatus-perf, Cache16 in main RAM, conditional single DMA
# (24 rows normal, 28 rows when HUD changes), 9.39 FPS / DEMO3 2134.
# NO routine profiler and NO graphics added after this baseline.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/hud
mkdir -p "$dest"; or exit 1

set -gx DOOM_TIMEDEMO 1
set -gx DOOM_NO_VSYNC 1
set -gx DOOM_FAST_DIVU 1
set -gx DOOM_CELL_LUT 1
set -gx DOOM_CACHE_SLOTS 16
set -gx DOOM_CACHE_STATS 0
set -gx DOOM_CLASSIC_TEXT_HUD 1
set -gx DOOM_HUD_DMA24 0
set -gx DOOM_HUD_DMA24_NOHUDWRITE 0
set -gx DOOM_HUD_DMA_STATUS_ONLY 1
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_MASKED_DIVU 0
set -gx DOOM_SRAM_CACHE16 0
set -gx DOOM_ZONE_KIB 0
set -gx DOOM_BUILD_ID doom-md-hudstatus-perf

echo "HUD: 38x24 text, Cache16 RAM, conditional 24/28-row DMA"
set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
# DOOM_ZONE_KIB is not a supported 0 value by build_silent.fish.
set -e DOOM_ZONE_KIB
fish scripts/build_silent.fish > "$logfile" 2>&1
if test $status -ne 0
    echo "Compilation failed. Last 70 log lines:"
    tail -n 70 "$logfile"
    exit 1
end

set -l flags (string match -r '^BUILD_FLAGS:.*' < "$logfile")
if test (count $flags) -ne 1
    echo 'ERROR: cannot verify exactly one compiler BUILD_FLAGS line'
    exit 1
end
for required in '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_FAST_DIVU' '-DDOOM_CELL_LUT' '-DVIEWWINDOWHEIGHT=24' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
    if not string match -q -- "*$required*" "$flags"
        echo "ERROR: missing canonical HUD compiler flag: $required"
        exit 1
    end
end
for forbidden in '-DDOOM_ROUTINE_PROFILE' '-DDOOM_PROFILE' '-DDOOM_HUD_DMA24 ' '-DDOOM_SRAM_CACHE16' '-DDOOM_CACHE_STATS'
    if string match -q -- "*$forbidden*" "$flags"
        echo "ERROR: non-reference compiler flag: $forbidden"
        exit 1
    end
end
if not test -s out/rom.bin; or not test -s out/release/rom.out
    echo 'ERROR: missing ROM or ELF'
    exit 1
end
python3 -c 'from pathlib import Path
b=Path("out/rom.bin").read_bytes()
n="doom-md-hudstatus-perf"
assert b[0x120:0x150].decode("ascii").strip()==n
assert b[0x150:0x180].decode("ascii").strip()==n
print("Validated HUD24 ROM:",n,len(b),"bytes")
'; or exit 1

cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
echo "READY: $dest/$DOOM_BUILD_ID.bin"
echo "Validate in BlastEm: 2134 frames, approx. 9.39 FPS at divider 7."
