#!/usr/bin/env fish
# Round W1: identical HUD24 control C vs M68000 inline ASM in textured walls.
# Produces two perf ROMs only. Neither changes the stable HUD24 source.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/hud-wallasm-w1
mkdir -p "$dest"; or exit 1

# fish block scoping is important. Export flags at script scope, not -l inside if.
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
set -gx DOOM_WALLCOL_ASM 0

for variant in c asm
    if test "$variant" = asm
        set -gx DOOM_WALLCOL_ASM 1
    else
        set -gx DOOM_WALLCOL_ASM 0
    end

    set -gx DOOM_BUILD_ID "doom-md-wallw1-$variant-perf"
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    echo "Building $DOOM_BUILD_ID"

    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "COMPILER ERROR: $DOOM_BUILD_ID"
        tail -n 60 "$logfile"
        exit 1
    end

    set -l flags (string match -r '^BUILD_FLAGS:.*' < "$logfile")
    if test (count $flags) -ne 1
        echo "ERROR: build did not record its compiler flags."
        exit 1
    end
    for needed in '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CELL_LUT' '-DDOOM_CACHE_SLOTS=16'
        if not string match -q "*$needed*" "$flags"
            echo "ERROR: missing build flag $needed"
            exit 1
        end
    end
    if test "$variant" = asm
        if not string match -q '*-DDOOM_WALLCOL_ASM*' "$flags"
            echo "ERROR: wall ASM flag missing in ASM build."
            exit 1
        end
    else
        if string match -q '*-DDOOM_WALLCOL_ASM*' "$flags"
            echo "ERROR: baseline was unexpectedly built with wall ASM."
            exit 1
        end
    end

    if not test -s out/rom.bin
        echo "ERROR: ROM missing for $DOOM_BUILD_ID"
        exit 1
    end
    python3 -c 'import pathlib,sys
b=pathlib.Path("out/rom.bin").read_bytes()
ident=sys.argv[1]
assert b[0x120:0x150].decode("ascii").strip()==ident
assert b[0x150:0x180].decode("ascii").strip()==ident
print("Verified:",ident, len(b),"bytes")
' "$DOOM_BUILD_ID"; or exit 1
    cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1

    # Save ELF/map symbols to investigate faults without confusing historic messages.
    cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
    if test -s out/release/symbol.txt
        cp out/release/symbol.txt "$dest/$DOOM_BUILD_ID.symbols.txt"
    end
end

echo ""
echo "Both control ROMs built successfully:"
ls -lh "$dest"/*.bin
echo "Test C baseline FIRST in BlastEm; then test ASM, with 2134-frame DEMO3."
echo "If ASM glitches, black-screens or hangs, stop; report result before new variants."
