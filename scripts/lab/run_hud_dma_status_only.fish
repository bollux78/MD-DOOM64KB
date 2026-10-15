#!/usr/bin/env fish
# 1-ROM controlled experiment: 24-row DMA, or 28 rows on three HUD value changes.
# Diff from successful dma24only ROM: 8 bytes of static status state +
# conditional height, but no 304-byte HUD snapshot or extra VDP call.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/hud-dma-status
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
set -gx DOOM_BUILD_ID doom-md-hudstatus-perf

echo "Building $DOOM_BUILD_ID"
fish scripts/build_silent.fish > "$dest/build-$DOOM_BUILD_ID.log" 2>&1
if test $status -ne 0
    echo "Compiler failed; last 40 log lines:"
    tail -n 40 "$dest/build-$DOOM_BUILD_ID.log"
    exit 1
end
if not grep -q -- '-DDOOM_HUD_DMA_STATUS_ONLY' "$dest/build-$DOOM_BUILD_ID.log"
    echo "ERROR: status-only macro missing in compile log"
    exit 1
end
if not grep -q -- '-DDOOM_CLASSIC_TEXT_HUD' "$dest/build-$DOOM_BUILD_ID.log"
    echo "ERROR: classic HUD macro missing in compile log"
    exit 1
end
if not test -s out/rom.bin
    echo "ERROR: out/rom.bin missing"
    exit 1
end
python3 -c 'from pathlib import Path
b=Path("out/rom.bin").read_bytes()
s="doom-md-hudstatus-perf"
assert b[0x120:0x150].decode("ascii").strip()==s
assert b[0x150:0x180].decode("ascii").strip()==s
print("Verified ROM identity:",s)
'; or exit 1
cp out/rom.bin "$dest/doom-md-hudstatus-perf.bin"; or exit 1
set -l nm "$HOME/mars/m68k-elf/bin/m68k-elf-nm"
if set -q DOOM_MD_GDK
    set nm "$DOOM_MD_GDK/bin/m68k-elf-nm"
end
python3 scripts/lab/ram_usage.py --elf out/release/rom.out \
    --nm "$nm" --variant "$DOOM_BUILD_ID" --fault-pc 0 \
    --output "$dest/ram-$DOOM_BUILD_ID.txt"; or exit 1
echo "READY: $dest/doom-md-hudstatus-perf.bin"
echo "BlastEm only. Keep stable HUD24 untouched."
