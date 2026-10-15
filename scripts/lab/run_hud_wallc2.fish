#!/usr/bin/env fish
# Controlled C-only Round C2: original wall-angle quadrant lookup versus
# direct 4096-entry tangent ROM table generated from original exact values.
# HUD24 conditional DMA, Cache16 RAM, no SRAM or ASM renderer changes.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/hud-wallc2
mkdir -p "$dest"; or exit 1

# Keep flags exported across Fish blocks (the previous -lx bug).
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
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_WALL_TAN_LUT 0

for variant in c lut
    if test "$variant" = lut
        set -gx DOOM_WALL_TAN_LUT 1
    else
        set -gx DOOM_WALL_TAN_LUT 0
    end

    set -gx DOOM_BUILD_ID "doom-md-wallc2-$variant-perf"
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    echo "Building $DOOM_BUILD_ID"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "BUILD FAILED: $DOOM_BUILD_ID"
        tail -n 70 "$logfile"
        exit 1
    end

    set -l flags (string match -r '^BUILD_FLAGS:.*' < "$logfile")
    if test (count $flags) -ne 1
        echo "ERROR: cannot verify compile flags: $DOOM_BUILD_ID"
        exit 1
    end
    for needed in '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CELL_LUT' '-DDOOM_CACHE_SLOTS=16'
        if not string match -q "*$needed*" "$flags"
            echo "ERROR: missing required compile flag: $needed"
            exit 1
        end
    end
    if test "$variant" = lut
        if not string match -q '*-DDOOM_WALL_TAN_LUT*' "$flags"
            echo 'ERROR: LUT build did not enable the optimization'
            exit 1
        end
        if not test -s src/wall_tangent_lut.h
            echo 'ERROR: generated tangent lookup header missing'
            exit 1
        end
    else
        if string match -q '*-DDOOM_WALL_TAN_LUT*' "$flags"
            echo 'ERROR: control ROM also enabled tangent lookup'
            exit 1
        end
    end
    if not test -s out/rom.bin; or not test -s out/release/rom.out
        echo "ERROR: missing ROM or ELF: $DOOM_BUILD_ID"
        exit 1
    end
    python3 -c 'from pathlib import Path
import sys
b=Path("out/rom.bin").read_bytes()
s=sys.argv[1]
assert b[0x120:0x150].decode("ascii").strip()==s
assert b[0x150:0x180].decode("ascii").strip()==s
print("Verified:",s,len(b),"bytes")
' "$DOOM_BUILD_ID"; or exit 1

    cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
    cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
    if test -s out/release/symbol.txt
        cp out/release/symbol.txt "$dest/$DOOM_BUILD_ID.symbols.txt"; or exit 1
    end
end

printf '%s\n' \
    'Round C2: C quadrant baseline vs exact ROM tangent LUT C variant.' \
    'Same 38x24 HUD, DMA status-only, 16 RAM cache entries.' \
    'ROM table uses 16 KiB of cartridge ROM; no new WRAM.' \
    'Keep the original control if LUT does not beat its FPS.' \
    'Compare only after BOTH DEMO3 ROMs finish 2134 frames.' \
    > "$dest/README.txt"
echo ""
echo "COMPLETE: two ROMs compiled"
ls -lh "$dest"/*.bin
echo "Start with C control. Then test LUT. Both in BlastEm, normal 68000 clock."
