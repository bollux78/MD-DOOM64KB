#!/usr/bin/env fish
# Celso MegalDoom-inspired HUD material-separated palettes, test ROM only.
# Keeps viewport 38x24 and the successful single conditional DMA strategy.
# This version uses 3 banks for HUD and 1 for world: visual/perf tradeoff.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/celso-hud-test
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
set -gx DOOM_HUD_CELSO_PALETTES 1
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_WALL_TAN_LUT 0
set -gx DOOM_WALLCOL_ASM 0
set -gx DOOM_BUILD_ID doom-md-celsohud-v1-perf

set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
echo "Building MegalDoom palette-isolation HUD test..."
fish scripts/build_silent.fish > "$logfile" 2>&1
if test $status -ne 0
    echo 'Build FAILED. Last 75 log lines:'
    tail -n 75 "$logfile"
    exit 1
end
set -l flags (string match -r '^BUILD_FLAGS:.*' < "$logfile")
if test (count $flags) -ne 1
    echo "ERROR: missing BUILD_FLAGS identity line"
    exit 1
end
for required in '-DDOOM_HUD_CELSO_PALETTES' '-DDOOM_HUD_WAD_ATLAS' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_CACHE_SLOTS=16' '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24'
    if not string match -q "*$required*" "$flags"
        echo "ERROR: required macro not enabled: $required"
        exit 1
    end
end
if not test -s out/rom.bin; or not test -s out/release/rom.out
    echo 'ERROR: missing compiled ELF or ROM'
    exit 1
end
python3 -c 'from pathlib import Path
import re
h=Path("src/gen_pal.h").read_text()
match=re.search(r"static const uint8_t genpal_cell\[256\]\s*=\s*\{([^}]+)\}",h,re.S)
assert match
values=[int(v) for v in re.findall(r"\d+",match.group(1))]
assert len(values)==256
assert min(values)>=42 and max(values)<56
b=Path("out/rom.bin").read_bytes()
name="doom-md-celsohud-v1-perf"
assert b[0x120:0x150].decode("ascii").strip()==name
assert b[0x150:0x180].decode("ascii").strip()==name
print("Verified HUD palette split / 14-color world:",len(b),"bytes")
'; or exit 1
cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
string match -r '^Dedicated HUD palettes:.*|^Experimental dedicated HUD:.*|^Sources:.*' < "$logfile"
echo ""
echo "READY: $dest/$DOOM_BUILD_ID.bin"
echo "Check metal/face/red numbers and 3D color quality before 2134-frame DEMO3."
echo "Do not replace baseline; this intentionally limits 3D view to 14 colors."
