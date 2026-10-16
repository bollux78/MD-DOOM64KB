#!/usr/bin/env fish
# R15: optimize heavy per-column texture multiplications on R12 LUT Full.
# R13 and R14 discarded. No geometry, precision, tiles or VDP changes.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r15-wallmul
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r15_wallmul.py; or exit 1
python3 scripts/lab/gen_r12_recip_lut.py --max-scale 65535; or exit 1

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
set -gx DOOM_R12_RECIP_LUT 65535
set -gx DOOM_R12_RECIP_MASKED 0
set -e DOOM_R13_MUL_DECOMP
set -e DOOM_R14_CLIPSCAN
set -e DOOM_R14_BBOXSCAN
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


for variant in control tanu tans setupu setups bothu boths
    set -gx DOOM_R15_TANMUL 0
    set -gx DOOM_R15_SETUPMUL 0
    switch $variant
        case control
            set -gx DOOM_BUILD_ID doom-md-hud-r15-control
        case tanu
            set -gx DOOM_R15_TANMUL 1
            set -gx DOOM_BUILD_ID doom-md-hud-r15-tanu
        case tans
            set -gx DOOM_R15_TANMUL 2
            set -gx DOOM_BUILD_ID doom-md-hud-r15-tans
        case setupu
            set -gx DOOM_R15_SETUPMUL 1
            set -gx DOOM_BUILD_ID doom-md-hud-r15-setupu
        case setups
            set -gx DOOM_R15_SETUPMUL 2
            set -gx DOOM_BUILD_ID doom-md-hud-r15-setups
        case bothu
            set -gx DOOM_R15_TANMUL 1
            set -gx DOOM_R15_SETUPMUL 1
            set -gx DOOM_BUILD_ID doom-md-hud-r15-bothu
        case boths
            set -gx DOOM_R15_TANMUL 2
            set -gx DOOM_R15_SETUPMUL 2
            set -gx DOOM_BUILD_ID doom-md-hud-r15-boths
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
    for required in '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DDOOM_R10_DIST_DIVU' '-DDOOM_R11_TOPBAR_CLIP' '-DDOOM_R11_LEFTCOL_CLIP' '-DDOOM_R12_RECIP_LUT' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing compiler flag $required"
            exit 1
        end
    end
    for forbidden in '-DDOOM_R10_RECIP_DIVU' '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R7_PROFILE' '-DDOOM_SRAM_CACHE16' '-DDOOM_R8_LUT_UNROLL' '-DDOOM_R8_SKIP_MASKED_RECIP' '-DDOOM_R11_TOPBAR_DMA' '-DDOOM_MASKED_DIVU' '-DDOOM_R12_RECIP_MASKED' '-DDOOM_R13_MUL_DECOMP' '-DDOOM_R14_CLIPSCAN' '-DDOOM_R14_BBOXSCAN'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unexpected compiler flag $forbidden"
            exit 1
        end
    end
    if test "$DOOM_R15_TANMUL" != 0
        string match -q -- "*-DDOOM_R15_TANMUL=$DOOM_R15_TANMUL*" "$flags"; or begin
            echo 'ERROR: R15 tangent multiply flag mismatch'
            exit 1
        end
    else if string match -q -- '*-DDOOM_R15_TANMUL*' "$flags"
        echo 'ERROR: R15 tangent flag present in control/setup variant'
        exit 1
    end
    if test "$DOOM_R15_SETUPMUL" != 0
        string match -q -- "*-DDOOM_R15_SETUPMUL=$DOOM_R15_SETUPMUL*" "$flags"; or begin
            echo 'ERROR: R15 setup multiply flag mismatch'
            exit 1
        end
    else if string match -q -- '*-DDOOM_R15_SETUPMUL*' "$flags"
        echo 'ERROR: R15 setup flag present in control/tangent variant'
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
    'R15 68000 exact signed 16x32 wall multiplications; R12 Full stable baseline: 10.12 FPS / 210.95s / DEMO3 2134 frames.' \
    'R13 and R14 discarded; original R12 FixedMul and original R12 clip/BSP memchr.' \
    'control: unmodified R12 Full, R15 macros disabled.' \
    'tanu: replace four per-column tangent products by two MULU.W and signed correction.' \
    'tans: same tangent products by signed-high and unsigned-low MULS/MULU.' \
    'setupu: optimize per-segment distance and texture-offset products using MULU.W.' \
    'setups: optimize per-segment products with signed-high MULS.W and MULU.W.' \
    'bothu: tangent + setup unsigned decomposition. boths: signed-high decomposition.' \
    'Both implementations preserve original low-32-bit wraparound and arithmetic >>16.' \
    'Arithmetic preflight is not a guarantee of in-game or real-hardware correctness.' \
    'BlastEm: NTSC60, stock 68000 divider7 (7.67MHz), fast-forward 1000%, DEMO3 2134 frames; repeat 3x.' \
    'Reject unstable variants; inspect wall textures, doors, masked sprites, and sky.' \
    > "$dest/README.txt"
echo 'READY: R15 seven ROMs'
