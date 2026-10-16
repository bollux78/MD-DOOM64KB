#!/usr/bin/env fish
# R12 exact reciprocal ROM LUT matrix on the user-verified R11 TopLeftClip.
# No changes to projection, tile count, visual quality, or game logic.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r12-recip
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r12_recip_lut.py; or exit 1

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
set -gx DOOM_R10_DIST_DIVU 1
set -gx DOOM_R10_RECIP_DIVU 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_MASKED_DIVU 0
set -gx DOOM_RAM_STATS 0
set -gx DOOM_SRAM_CACHE16 0
set -gx DOOM_SRAM_FASTCOPY 0
set -gx DOOM_R8_LUT_UNROLL 0
set -gx DOOM_R8_SKIP_MASKED_RECIP 0
set -gx DOOM_R11_TOPBAR_CLIP 1
set -gx DOOM_R11_TOPBAR_DMA 0
set -gx DOOM_R11_LEFTCOL_CLIP 1
set -e DOOM_ZONE_KIB

for variant in control lut4k lut16k lutfull lutfullmasked
    set -gx DOOM_R12_RECIP_LUT 0
    set -gx DOOM_R12_RECIP_MASKED 0
    set -l limit 0
    switch $variant
        case control
            set -gx DOOM_BUILD_ID doom-md-hud-r12-control
        case lut4k
            set -l limit 4095
            set -gx DOOM_R12_RECIP_LUT $limit
            set -gx DOOM_BUILD_ID doom-md-hud-r12-lut4k
        case lut16k
            set -l limit 16383
            set -gx DOOM_R12_RECIP_LUT $limit
            set -gx DOOM_BUILD_ID doom-md-hud-r12-lut16k
        case lutfull
            set -l limit 65535
            set -gx DOOM_R12_RECIP_LUT $limit
            set -gx DOOM_BUILD_ID doom-md-hud-r12-lutfull
        case lutfullmasked
            set -l limit 65535
            set -gx DOOM_R12_RECIP_LUT $limit
            set -gx DOOM_R12_RECIP_MASKED 1
            set -gx DOOM_BUILD_ID doom-md-hud-r12-lutfullmasked
    end

    if test "$DOOM_R12_RECIP_LUT" != 0
        python3 scripts/lab/gen_r12_recip_lut.py --max-scale $DOOM_R12_RECIP_LUT; or exit 1
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
    for required in '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DDOOM_R10_DIST_DIVU' '-DDOOM_R11_TOPBAR_CLIP' '-DDOOM_R11_LEFTCOL_CLIP' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing compiler flag $required"
            exit 1
        end
    end
    for forbidden in '-DDOOM_R10_RECIP_DIVU' '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R7_PROFILE' '-DDOOM_SRAM_CACHE16' '-DDOOM_R8_LUT_UNROLL' '-DDOOM_R8_SKIP_MASKED_RECIP' '-DDOOM_R11_TOPBAR_DMA' '-DDOOM_MASKED_DIVU'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unexpected compiler flag $forbidden"
            exit 1
        end
    end
    if test "$DOOM_R12_RECIP_LUT" != 0
        string match -q -- '*-DDOOM_R12_RECIP_LUT*' "$flags"; or begin
            echo 'ERROR: R12 LUT flag missing'
            exit 1
        end
    else if string match -q -- '*-DDOOM_R12_RECIP_LUT*' "$flags"
        echo 'ERROR: R12 LUT flag on control'
        exit 1
    end
    if test "$DOOM_R12_RECIP_MASKED" = 1
        string match -q -- '*-DDOOM_R12_RECIP_MASKED*' "$flags"; or exit 1
    else if string match -q -- '*-DDOOM_R12_RECIP_MASKED*' "$flags"
        echo 'ERROR: masked flag on non-masked variant'
        exit 1
    end
    python3 -c 'import pathlib,sys
b=pathlib.Path("out/rom.bin").read_bytes()
name=sys.argv[1]
assert 0x200 <= len(b) < 0x400000, len(b)
assert b[0x120:0x150].decode("ascii").strip()==name
assert b[0x150:0x180].decode("ascii").strip()==name
print("VERIFIED",name,len(b),"bytes")
' "$DOOM_BUILD_ID"; or exit 1
    cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
    cp out/.render_options "$dest/flags-$DOOM_BUILD_ID.txt"; or exit 1
    if test -s out/release/rom.out
        cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
        if test -x "$HOME/mars/m68k-elf/bin/m68k-elf-objdump"
            "$HOME/mars/m68k-elf/bin/m68k-elf-objdump" -d out/release/rom.out > "$dest/disassembly-$DOOM_BUILD_ID.txt"; or exit 1
        end
        if test -x "$HOME/mars/m68k-elf/bin/m68k-elf-size"
            "$HOME/mars/m68k-elf/bin/m68k-elf-size" out/release/rom.out > "$dest/size-$DOOM_BUILD_ID.txt"
        end
    end
end
printf '%s\n' \
    'R12 exact reciprocal lookup. R11 TopLeftClip control: 10.07 FPS / 212.02 s DEMO3, user measurement.' \
    'LUT4K: 7 KiB ROM table, scale 512..4095; LUT16K: 31 KiB, scale 512..16383.' \
    'LUTFULL: 127 KiB, scale 512..65535; LUTFULLMASKED: same LUT also for masked mid textures.' \
    'Bit-identical 16-bit fractional step for all legal scales; out-of-range retains R11 DIVU or original masked FixedReciprocal.' \
    'ROM table size trades cartridge space against expensive 68000 DIVU.W operations; measure on real Mega Drive too.' \
    'BlastEm: NTSC60, stock 68000 divider7, 1000% fast-forward, DEMO3 2134 frames. Repeat 3x and inspect sprites/doors/sky.' \
    'Do not merge an unmeasured variant; test gameplay beyond timedemo and real hardware before choosing.' \
    > "$dest/README.txt"
echo 'READY: R12 five ROMs'
