#!/usr/bin/env fish
# Canonical FULLSCREEN 38x28 benchmark.
# Reference: R6 "sramasm-perf", cache16 in odd-lane SRAM with 68000
# DBRA-based copying; measured ~8.86 FPS on 2134-frame DEMO3.
# Based exactly on R6 run_round6.fish options, but builds ONE ROM.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/fullscreen
mkdir -p "$dest"; or exit 1

set -gx DOOM_TIMEDEMO 1
set -gx DOOM_NO_VSYNC 1
set -gx DOOM_FAST_DIVU 1
set -gx DOOM_CELL_LUT 1
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_MASKED_DIVU 0
set -gx DOOM_CACHE8 0
set -gx DOOM_CACHE_SLOTS 16
set -gx DOOM_RAM_STATS 0
set -gx DOOM_ZONE_KIB 43
set -gx DOOM_SRAM_CACHE16 1
set -gx DOOM_SRAM_FASTCOPY 1
set -gx DOOM_SRAM_HOT_SLOTS 0
set -gx DOOM_CACHE_STATS 0
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_CLASSIC_TEXT_HUD 0
set -gx DOOM_BUILD_ID doom-md-r6-sramasm-perf

echo "FULLSCREEN: R6 Cache16 SRAM ASM - 38x28 - no HUD"
set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
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
for required in '-DDOOM_SRAM_CACHE16' '-DDOOM_SRAM_FASTCOPY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_FAST_DIVU' '-DDOOM_CELL_LUT' '-DVIEWWINDOWHEIGHT=28' '-DHEAP_SIZE=44032' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
    if not string match -q -- "*$required*" "$flags"
        echo "ERROR: missing R6 SRAM ASM option: $required"
        exit 1
    end
end
for forbidden in '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_SRAM_HOT_SLOTS=' '-DDOOM_ROUTINE_PROFILE' '-DDOOM_PROFILE' '-DDOOM_CACHE_STATS'
    if string match -q -- "*$forbidden*" "$flags"
        echo "ERROR: non-reference compiler option: $forbidden"
        exit 1
    end
end
if not test -s out/rom.bin; or not test -s out/release/rom.out
    echo 'ERROR: missing ROM or ELF'
    exit 1
end
python3 -c 'from pathlib import Path
import struct
b=Path("out/rom.bin").read_bytes()
n="doom-md-r6-sramasm-perf"
assert len(b)<0x200000, "ROM overlaps SRAM cartridge address"
assert b[0x120:0x150].decode("ascii").strip()==n
assert b[0x150:0x180].decode("ascii").strip()==n
assert b[0x1B0:0x1B2]==b"RA", "ROM header lacks SRAM"
assert struct.unpack_from(">II",b,0x1B4)==(0x200000,0x20FFFF)
print("Validated R6 SRAM ASM ROM:",n,len(b),"bytes")
'; or exit 1

cp out/rom.bin "$dest/doom-md-fullscreen-sramasm-perf.bin"; or exit 1
cp out/release/rom.out "$dest/doom-md-fullscreen-sramasm-perf.elf"; or exit 1
echo "READY: $dest/doom-md-fullscreen-sramasm-perf.bin"
echo "Internal ROM title remains: doom-md-r6-sramasm-perf (original R6)."
echo "Only the output filename was renamed, not ROM header or linked layout."
echo "Validate in BlastEm: 2134 frames, approx. 8.86 FPS at divider 7."
echo "This R6 SRAM configuration was originally an emulator experiment."
