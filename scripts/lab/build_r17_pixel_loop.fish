#!/usr/bin/env fish
# R17: optimize hot pixel loops using MC68000 DBRA and 16-bit initial fraction multiplication.
# Use R16 hand1 (real hardware 10.20 FPS) as the sole geometry baseline.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r17-pixel-loop
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r15_wallmul.py; or exit 1
python3 scripts/lab/test_r16_crt_hud.py; or exit 1
python3 scripts/lab/test_r17_pixel_loop.py; or exit 1
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



# R16 hand1 validated on CRT and original 7.67 MHz Mega Drive at 10.20 FPS.
set -gx DOOM_R15_TANMUL 0
set -gx DOOM_R15_SETUPMUL 1

set -gx DOOM_R16_HUD_UP2 1
set -gx DOOM_R16_WEAPON_LIFT 1
for variant in control fracmul dbra combined
    set -gx DOOM_R17_PIXEL_DBRA 0
    set -gx DOOM_R17_FRAC_MULU 0
    switch $variant
        case control
            set -gx DOOM_BUILD_ID doom-md-hud-r17-control
        case fracmul
            set -gx DOOM_R17_FRAC_MULU 1
            set -gx DOOM_BUILD_ID doom-md-hud-r17-fracmul
        case dbra
            set -gx DOOM_R17_PIXEL_DBRA 1
            set -gx DOOM_BUILD_ID doom-md-hud-r17-dbra
        case combined
            set -gx DOOM_R17_PIXEL_DBRA 1
            set -gx DOOM_R17_FRAC_MULU 1
            set -gx DOOM_BUILD_ID doom-md-hud-r17-combined
    end
    echo "BUILD: $DOOM_BUILD_ID"
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "ERROR: compile failed for $DOOM_BUILD_ID"
        tail -n 110 "$logfile"
        exit 1
    end
    test -s out/rom.bin; or exit 1
    test -s out/.render_options; or exit 1
    set -l flags (cat out/.render_options)
    for required in '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=22' '-DDOOM_R16_HUD_UP2' '-DDOOM_R16_WEAPON_LIFT=1' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DDOOM_R10_DIST_DIVU' '-DDOOM_R11_TOPBAR_CLIP' '-DDOOM_R11_LEFTCOL_CLIP' '-DDOOM_R12_RECIP_LUT' '-DDOOM_R15_SETUPMUL=1' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
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
    if test "$DOOM_R17_PIXEL_DBRA" = 1
        string match -q -- '*-DDOOM_R17_PIXEL_DBRA*' "$flags"; or exit 1
    else if string match -q -- '*-DDOOM_R17_PIXEL_DBRA*' "$flags"
        echo 'ERROR: unwanted R17 DBRA'
        exit 1
    end
    if test "$DOOM_R17_FRAC_MULU" = 1
        string match -q -- '*-DDOOM_R17_FRAC_MULU*' "$flags"; or exit 1
    else if string match -q -- '*-DDOOM_R17_FRAC_MULU*' "$flags"
        echo 'ERROR: unwanted R17 MULU'
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
    end
end
printf '%s\n' \
    'R17 pixel loop. Base: R16 hand1 stable original Mega Drive 7.67MHz, 10.20 FPS.' \
    'Control: R16 hand1 unchanged (38x22, HUD up 2, weapon up 1, R15 setupu).' \
    'fracmul: 16x16 MULU.W for initial texture fraction, exact modulo 65536.' \
    'dbra: 68000 DBRA pixel loop for standard COLORMAP only, C fallback unchanged.' \
    'combined: both optimizations.' \
    'Benchmark: BlastEm NTSC60 divider7 DEMO3 2134 frames; verify each ROM.' \
    'CRT: check wall textures, weapons, sprites, palettes and no black-screen hangs.' \
    > "$dest/README.txt"
echo 'READY: R17 four ROMs'
