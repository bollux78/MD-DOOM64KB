#!/usr/bin/env fish
# HUD24 R10: independent exact 68000 DIVU.W paths on top of verified R9 Combined.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r10
mkdir -p "$dest"; or exit 1

python3 scripts/lab/test_r10_math.py; or exit 1

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
set -gx DOOM_PROFILE 0
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_R7_PROFILE 0
set -gx DOOM_R9_SLOPE_DIVU 1
set -gx DOOM_R9_STEP_DIVS 1
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_MASKED_DIVU 0
set -gx DOOM_RAM_STATS 0
set -gx DOOM_SRAM_CACHE16 0
set -gx DOOM_SRAM_FASTCOPY 0
set -gx DOOM_R8_LUT_UNROLL 0
set -gx DOOM_R8_SKIP_MASKED_RECIP 0
set -e DOOM_ZONE_KIB

for variant in base dist recip combined
    set -gx DOOM_R10_DIST_DIVU 0
    set -gx DOOM_R10_RECIP_DIVU 0
    switch $variant
        case base
            set -gx DOOM_BUILD_ID doom-md-hud-r10-base
        case dist
            set -gx DOOM_R10_DIST_DIVU 1
            set -gx DOOM_BUILD_ID doom-md-hud-r10-dist
        case recip
            set -gx DOOM_R10_RECIP_DIVU 1
            set -gx DOOM_BUILD_ID doom-md-hud-r10-recip
        case combined
            set -gx DOOM_R10_DIST_DIVU 1
            set -gx DOOM_R10_RECIP_DIVU 1
            set -gx DOOM_BUILD_ID doom-md-hud-r10-combined
    end
    echo "BUILD: $DOOM_BUILD_ID"
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "ERROR: compile failed for $DOOM_BUILD_ID"
        tail -n 100 "$logfile"
        exit 1
    end
    test -s out/rom.bin; or exit 1
    test -s out/.render_options; or exit 1
    set -l flags (cat out/.render_options)
    for required in '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing expected compiler flag $required"
            exit 1
        end
    end
    for forbidden in '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R7_PROFILE' '-DDOOM_SRAM_CACHE16' '-DDOOM_R8_LUT_UNROLL' '-DDOOM_R8_SKIP_MASKED_RECIP'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unexpected performance flag $forbidden"
            exit 1
        end
    end
    if test $DOOM_R10_DIST_DIVU -eq 1
        string match -q -- '*-DDOOM_R10_DIST_DIVU*' "$flags"; or exit 1
    else if string match -q -- '*-DDOOM_R10_DIST_DIVU*' "$flags"
        echo 'ERROR: unexpected R10 distance flag'
        exit 1
    end
    if test $DOOM_R10_RECIP_DIVU -eq 1
        string match -q -- '*-DDOOM_R10_RECIP_DIVU*' "$flags"; or exit 1
    else if string match -q -- '*-DDOOM_R10_RECIP_DIVU*' "$flags"
        echo 'ERROR: unexpected R10 reciprocal flag'
        exit 1
    end
    python3 -c 'import pathlib,sys
b=pathlib.Path("out/rom.bin").read_bytes()
name=sys.argv[1]
assert 0x200 <= len(b) < 0x200000
assert b[0x120:0x150].decode("ascii").strip()==name
assert b[0x150:0x180].decode("ascii").strip()==name
print("VERIFIED",name,len(b))
' "$DOOM_BUILD_ID"; or exit 1
    cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
    cp out/.render_options "$dest/flags-$DOOM_BUILD_ID.txt"; or exit 1
    if test -s out/release/rom.out
        cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
        if test -x "$HOME/mars/m68k-elf/bin/m68k-elf-objdump"
            "$HOME/mars/m68k-elf/bin/m68k-elf-objdump" -d out/release/rom.out > "$dest/disassembly-$DOOM_BUILD_ID.txt"; or exit 1
        end
    end
end
printf '%s\n' \
    'R10: four uninstrumented ROMs; each retains validated R9 combined slope DIVU + scale DIVS.' \
    'base: historical expectation 9.80 FPS, 217.72 emulated s on DEMO3 2134 frames.' \
    'dist: guarded hardware DIVU.W for final R_PointToDist signed positive quotient.' \
    'recip: EXACT 0xffffffff/divisor using two hardware DIVU.W for 1..65535 in FixedApproxDiv.' \
    'combined: both experimental R10 changes.' \
    'Arithmetic preflight compares all positive 16-bit reciprocal denominators.' \
    'Compile success does NOT establish speedup or full runtime correctness. Visual QA required.' \
    'NTSC60, NO VSYNC, BlastEm stock 68000 divider 7, user-verified emulator fast forward 1000%.' \
    > "$dest/README.txt"
echo 'READY: R10 four ROMs'
