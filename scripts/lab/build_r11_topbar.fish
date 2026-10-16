#!/usr/bin/env fish
# R11 top telemetry row: preserve R10 Dist 7.67 MHz, 38x24 projection.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r11
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r11_topbar.py; or exit 1

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
set -e DOOM_ZONE_KIB

for variant in base clip clipdma
    set -gx DOOM_R11_TOPBAR_CLIP 0
    set -gx DOOM_R11_TOPBAR_DMA 0
    switch $variant
        case base
            set -gx DOOM_BUILD_ID doom-md-hud-r11-base
        case clip
            set -gx DOOM_R11_TOPBAR_CLIP 1
            set -gx DOOM_BUILD_ID doom-md-hud-r11-topclip
        case clipdma
            set -gx DOOM_R11_TOPBAR_CLIP 1
            set -gx DOOM_R11_TOPBAR_DMA 1
            set -gx DOOM_BUILD_ID doom-md-hud-r11-topdma
    end
    echo "BUILD: $DOOM_BUILD_ID"
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "ERROR: build failed $DOOM_BUILD_ID"
        tail -n 100 "$logfile"
        exit 1
    end
    test -s out/rom.bin; or exit 1
    test -s out/.render_options; or exit 1
    set -l flags (cat out/.render_options)
    for required in '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DDOOM_R10_DIST_DIVU' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing compiler flag $required"
            exit 1
        end
    end
    for forbidden in '-DDOOM_R10_RECIP_DIVU' '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R7_PROFILE' '-DDOOM_SRAM_CACHE16' '-DDOOM_R8_LUT_UNROLL' '-DDOOM_R8_SKIP_MASKED_RECIP'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unexpected compiler flag $forbidden"
            exit 1
        end
    end
    for switch in CLIP DMA
        set -l enabled 0
        if test $switch = CLIP
            set enabled $DOOM_R11_TOPBAR_CLIP
        else
            set enabled $DOOM_R11_TOPBAR_DMA
        end
        if test $enabled -eq 1
            string match -q -- "*-DDOOM_R11_TOPBAR_$switch*" "$flags"; or begin
                echo "ERROR: missing R11 switch $switch"
                exit 1
            end
        else if string match -q -- "*-DDOOM_R11_TOPBAR_$switch*" "$flags"
            echo "ERROR: unexpected R11 switch $switch"
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
        if test -x "$HOME/mars/m68k-elf/bin/m68k-elf-objdump"
            "$HOME/mars/m68k-elf/bin/m68k-elf-objdump" -d out/release/rom.out > "$dest/disassembly-$DOOM_BUILD_ID.txt"; or exit 1
        end
    end
end
printf '%s\n' \
    'R11 TOP BAR — three uninstrumented ROMs, R10 Dist baseline (9.85 FPS BlastEm, 9.77 real Mega Drive at stock 7.67 MHz).' \
    'base: identical feature flags to R10 Dist, full row0 3D rendering and original status-only DMA.' \
    'topclip: clip walls, sky, sprites, weapon sprites and automap at row0; FPS and gameplay messages can use black row0.' \
    'topdma: same clipping plus skip row0 in single VDP DMA whenever its actual 38 tile words are unchanged.' \
    'All preserve original VIEWWINDOWHEIGHT=24 projection and physical 28-row HUD layout; visible 3D pixels are y1..23.' \
    'DMA on topdma: rows1..23 if unchanged, rows1..27 when bottom HUD changes, row0 included whenever telemetry changes.' \
    'Expected DMA savings: 38 cells = 76 bytes on unchanged top row; NOT an FPS guarantee.' \
    'Run BlastEm divider7, NTSC60, 1000% fast-forward, DEMO3 2134 frames; check black top bar, FPS, sprites, menu, automap and messages.' \
    'R10 RECIP remains DISABLED due to performance regression and observed combined crash.' \
    > "$dest/README.txt"
echo 'READY: R11 three ROMs'
