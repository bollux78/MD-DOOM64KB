#!/usr/bin/env fish
# R11 topleftclip: compare verified topclip to one more excluded x=0 column.
# Arithmetic base: R10 Dist (R9 slope+step, R10 distance), no R10 reciprocal.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r11-topleft
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r11_topleftclip.py; or exit 1

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
set -e DOOM_ZONE_KIB

for variant in topclip topleftclip
    set -gx DOOM_R11_LEFTCOL_CLIP 0
    switch $variant
        case topclip
            set -gx DOOM_BUILD_ID doom-md-hud-r11-topclip
        case topleftclip
            set -gx DOOM_R11_LEFTCOL_CLIP 1
            set -gx DOOM_BUILD_ID doom-md-hud-r11-topleftclip
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
    for required in '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DDOOM_R10_DIST_DIVU' '-DDOOM_R11_TOPBAR_CLIP' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing compiler flag $required"
            exit 1
        end
    end
    for forbidden in '-DDOOM_R10_RECIP_DIVU' '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R7_PROFILE' '-DDOOM_SRAM_CACHE16' '-DDOOM_R8_LUT_UNROLL' '-DDOOM_R8_SKIP_MASKED_RECIP' '-DDOOM_R11_TOPBAR_DMA'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unexpected compiler flag $forbidden"
            exit 1
        end
    end
    if test "$DOOM_R11_LEFTCOL_CLIP" = 1
        string match -q -- '*-DDOOM_R11_LEFTCOL_CLIP*' "$flags"; or begin
            echo "ERROR: missing left-column clipping flag"
            exit 1
        end
    else if string match -q -- '*-DDOOM_R11_LEFTCOL_CLIP*' "$flags"
        echo "ERROR: unexpected left-column clipping flag"
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
    'R11 TOPLEFTCLIP: both ROMs use R10 Dist arithmetic (R9 slope/step + R10 distance) and R11 topclip, no top-row DMA skip.' \
    'topclip: user-repeated 9.90 FPS, 215.58 seconds for DEMO3 2134 frames in BlastEm, NTSC 60Hz.' \
    'topleftclip: marks x=0 as solid in BSP clip, clamps projected world/weapon sprites x>=1 with corrected startfrac, skips automap x0.' \
    'Clear the black left border once on level entry; keep FPS text in top row and bottom text HUD.' \
    'Preserve original 38x24 projection and 38-wide framebuffer; effective rendered world is 37x23 cells (x1..37, y1..23).' \
    'No 37-wide row stride, no projection shift, no 13MHz overclock, no extra DMA branch.' \
    'Run BlastEm stock 68000 divider7, NTSC60, 1000% fast-forward; DEMO3 2134 frames.' \
    'Visual QA: black left border, no sprite/weapon/sky leaks, correct menu and automap; run at least 3 times before promoting.' \
    > "$dest/README.txt"
echo 'READY: R11 TOPLEFTCLIP two ROMs'
