#!/usr/bin/env fish
# R16: move the classic HUD two tile rows up for real CRT overscan.
# Keep proven R15 setupu as control. R16 uses 22-row reprojection, not crop.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r16-crt-hud
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r15_wallmul.py; or exit 1
python3 scripts/lab/test_r16_crt_hud.py; or exit 1
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



# Real-hardware stable R15 setupu at 7.67 MHz: 10.04 FPS / 212.48 s.
# Preserve this exact baseline and change only the R16 HUD/view geometry.
set -gx DOOM_R15_TANMUL 0
set -gx DOOM_R15_SETUPMUL 1
for variant in control up2 hand1 hand2
    set -gx DOOM_R16_HUD_UP2 0
    set -gx DOOM_R16_WEAPON_LIFT 0
    switch $variant
        case control
            set -gx DOOM_BUILD_ID doom-md-hud-r16-control
        case up2
            set -gx DOOM_R16_HUD_UP2 1
            set -gx DOOM_BUILD_ID doom-md-hud-r16-up2
        case hand1
            set -gx DOOM_R16_HUD_UP2 1
            set -gx DOOM_R16_WEAPON_LIFT 1
            set -gx DOOM_BUILD_ID doom-md-hud-r16-hand1
        case hand2
            set -gx DOOM_R16_HUD_UP2 1
            set -gx DOOM_R16_WEAPON_LIFT 2
            set -gx DOOM_BUILD_ID doom-md-hud-r16-hand2
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
    for required in '-DVIEWWINDOWWIDTH=38' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DDOOM_R10_DIST_DIVU' '-DDOOM_R11_TOPBAR_CLIP' '-DDOOM_R11_LEFTCOL_CLIP' '-DDOOM_R12_RECIP_LUT' '-DDOOM_R15_SETUPMUL=1' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing compiler flag $required"
            exit 1
        end
    end
    for forbidden in '-DDOOM_R10_RECIP_DIVU' '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R7_PROFILE' '-DDOOM_SRAM_CACHE16' '-DDOOM_R8_LUT_UNROLL' '-DDOOM_R8_SKIP_MASKED_RECIP' '-DDOOM_R11_TOPBAR_DMA' '-DDOOM_MASKED_DIVU' '-DDOOM_R12_RECIP_MASKED' '-DDOOM_R13_MUL_DECOMP' '-DDOOM_R14_CLIPSCAN' '-DDOOM_R14_BBOXSCAN' '-DDOOM_R15_TANMUL'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unexpected compiler flag $forbidden"
            exit 1
        end
    end
    if test "$DOOM_R16_HUD_UP2" = 1
        string match -q -- '*-DVIEWWINDOWHEIGHT=22*' "$flags"; or begin
            echo 'ERROR: R16 must use true 22-row viewport'
            exit 1
        end
        string match -q -- '*-DDOOM_R16_HUD_UP2*' "$flags"; or exit 1
        if test "$DOOM_R16_WEAPON_LIFT" != 0
            string match -q -- "*-DDOOM_R16_WEAPON_LIFT=$DOOM_R16_WEAPON_LIFT*" "$flags"; or exit 1
        else if string match -q -- '*-DDOOM_R16_WEAPON_LIFT*' "$flags"
            echo 'ERROR: weapon lift flag unexpectedly enabled'
            exit 1
        end
    else
        string match -q -- '*-DVIEWWINDOWHEIGHT=24*' "$flags"; or exit 1
        if string match -q -- '*-DDOOM_R16_HUD_UP2*' "$flags"
            echo 'ERROR: R16 HUD flag in R15 control'
            exit 1
        end
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
    end
end
printf '%s\n' \
    'R16 CRT HUD experiment: real Mega Drive stock 7.67 MHz R15 setupu reference 10.04 FPS / 212.48s.' \
    'R15 setupu is the CONTROL: same 38x24 viewport, HUD text rows 25 and 27.' \
    'up2: true 38x22 viewport, HUD text rows 23 and 25, rows 26 and 27 black.' \
    'hand1: up2 with first-person weapon raised 1 tile row (8 pixels).' \
    'hand2: up2 with first-person weapon raised 2 tile rows (16 pixels).' \
    'R16 recalculates projection, weapon scale, wall and sprite clipping for height 22.' \
    'Do not crop the old 24-row render: this avoids needlessly losing the gun hand.' \
    'Rows 26-27 remain black to protect the HUD text from CRT overscan.' \
    'Check the pistol and shotgun firing animations and the lower screen edges.' \
    'BlastEm: DEMO3 NTSC60, stock 68000 divider7, 2134 frames; verify all four ROMs.' \
    'CRT: visually compare hand visibility, HUD text visibility and black overscan margin.' \
    > "$dest/README.txt"
echo 'READY: R16 four ROMs'
