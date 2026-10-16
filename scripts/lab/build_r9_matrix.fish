#!/usr/bin/env fish
# R9: stock 68000 exact arithmetic matrix, HUD24 38x24, baseline uninstrumented.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r9
mkdir -p "$dest"; or exit 1

python3 scripts/lab/test_r9_math.py; or exit 1

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
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_MASKED_DIVU 0
set -gx DOOM_RAM_STATS 0
set -gx DOOM_SRAM_CACHE16 0
set -gx DOOM_SRAM_FASTCOPY 0
set -gx DOOM_R8_LUT_UNROLL 0
set -gx DOOM_R8_SKIP_MASKED_RECIP 0
set -e DOOM_ZONE_KIB

for variant in base slope step combined
    set -gx DOOM_R9_SLOPE_DIVU 0
    set -gx DOOM_R9_STEP_DIVS 0
    switch $variant
        case base
            set -gx DOOM_BUILD_ID doom-md-hud-r9-base
        case slope
            set -gx DOOM_R9_SLOPE_DIVU 1
            set -gx DOOM_BUILD_ID doom-md-hud-r9-slope
        case step
            set -gx DOOM_R9_STEP_DIVS 1
            set -gx DOOM_BUILD_ID doom-md-hud-r9-step
        case combined
            set -gx DOOM_R9_SLOPE_DIVU 1
            set -gx DOOM_R9_STEP_DIVS 1
            set -gx DOOM_BUILD_ID doom-md-hud-r9-combined
    end
    echo "BUILD: $DOOM_BUILD_ID"
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "ERROR: compilation failed for $DOOM_BUILD_ID"
        tail -n 85 "$logfile"
        exit 1
    end
    test -s out/rom.bin; or exit 1
    test -s out/.render_options; or exit 1
    set -l flags (cat out/.render_options)
    for required in '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing expected flag $required"
            exit 1
        end
    end
    for forbidden in '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R7_PROFILE' '-DDOOM_SRAM_CACHE16' '-DDOOM_R8_LUT_UNROLL' '-DDOOM_R8_SKIP_MASKED_RECIP'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unexpected performance configuration $forbidden"
            exit 1
        end
    end
    for switch in SLOPE_DIVU STEP_DIVS
        set -l enabled 0
        if test $switch = SLOPE_DIVU
            set enabled $DOOM_R9_SLOPE_DIVU
        else
            set enabled $DOOM_R9_STEP_DIVS
        end
        if test $enabled -eq 1
            string match -q -- "*-DDOOM_R9_$switch*" "$flags"; or begin
                echo "ERROR: missing R9 option $switch"
                exit 1
            end
        else if string match -q -- "*-DDOOM_R9_$switch*" "$flags"
            echo "ERROR: unexpected R9 option $switch"
            exit 1
        end
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
        if type -q m68k-elf-objdump
            m68k-elf-objdump -d out/release/rom.out > "$dest/assembly-$DOOM_BUILD_ID.txt"; or exit 1
        end
    end
end
printf '%s\n' \
    'DOOM Mega Drive R9 - exactly four UNINSTRUMENTED ROMs, same HUD24 38x24 and cache16 WRAM.' \
    'Base performance: 9.39 FPS (DEMO3 2134 frames, NTSC 60 Hz, BlastEm M68K divider 7).' \
    'slope: guarded DIVU.W for 11-bit-angle slope mapping (n<=d), otherwise original uint32 division.' \
    'step: guarded DIVS.W for scale interpolation, otherwise original int32 division.' \
    'combined: both optimizations; independent fast paths, same arithmetic results.' \
    'These are candidate micro-optimizations; no FPS improvement claimed before timedemo.' \
    'Use BlastEm 1000% fast forward, divider 7 (no CPU clock overclock), compare screenshots.' \
    'Logs, flags, ELF and compiled disassembly included where available.' \
    > "$dest/README.txt"
echo 'READY: R9 four ROMs'
