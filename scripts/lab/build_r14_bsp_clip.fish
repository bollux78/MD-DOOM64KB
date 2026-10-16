#!/usr/bin/env fish
# R14 clipping/BSP scan matrix; R12 LUT Full baseline. R13 discarded.
# Exact pixels and 38x24 projection preserved.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r14-bsp
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r14_clip.py; or exit 1
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


for variant in control clip1 clip2 bbox clip1bbox clip2bbox
    set -gx DOOM_R14_CLIPSCAN 0
    set -gx DOOM_R14_BBOXSCAN 0
    switch $variant
        case control
            set -gx DOOM_BUILD_ID doom-md-hud-r14-control
        case clip1
            set -gx DOOM_R14_CLIPSCAN 1
            set -gx DOOM_BUILD_ID doom-md-hud-r14-clip1
        case clip2
            set -gx DOOM_R14_CLIPSCAN 2
            set -gx DOOM_BUILD_ID doom-md-hud-r14-clip2
        case bbox
            set -gx DOOM_R14_BBOXSCAN 1
            set -gx DOOM_BUILD_ID doom-md-hud-r14-bbox
        case clip1bbox
            set -gx DOOM_R14_CLIPSCAN 1
            set -gx DOOM_R14_BBOXSCAN 1
            set -gx DOOM_BUILD_ID doom-md-hud-r14-clip1bbox
        case clip2bbox
            set -gx DOOM_R14_CLIPSCAN 2
            set -gx DOOM_R14_BBOXSCAN 1
            set -gx DOOM_BUILD_ID doom-md-hud-r14-clip2bbox
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
    for forbidden in '-DDOOM_R10_RECIP_DIVU' '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R7_PROFILE' '-DDOOM_SRAM_CACHE16' '-DDOOM_R8_LUT_UNROLL' '-DDOOM_R8_SKIP_MASKED_RECIP' '-DDOOM_R11_TOPBAR_DMA' '-DDOOM_MASKED_DIVU' '-DDOOM_R12_RECIP_MASKED' '-DDOOM_R13_MUL_DECOMP'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unexpected compiler flag $forbidden"
            exit 1
        end
    end
    if test "$DOOM_R14_CLIPSCAN" != 0
        string match -q -- "*-DDOOM_R14_CLIPSCAN=$DOOM_R14_CLIPSCAN*" "$flags"; or begin
            echo 'ERROR: R14 clip flag mismatch'
            exit 1
        end
    else if string match -q -- '*-DDOOM_R14_CLIPSCAN*' "$flags"
        echo 'ERROR: clip flag on non-clip variant'
        exit 1
    end
    if test "$DOOM_R14_BBOXSCAN" = 1
        string match -q -- '*-DDOOM_R14_BBOXSCAN*' "$flags"; or begin
            echo 'ERROR: R14 bbox flag missing'
            exit 1
        end
    else if string match -q -- '*-DDOOM_R14_BBOXSCAN*' "$flags"
        echo 'ERROR: bbox flag on non-bbox variant'
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
    'R14 short-column clipping and BSP bbox visibility scans. Baseline R12 LUT Full user result 10.12 FPS / 210.95 s / 2134 frames.' \
    'R13 discarded: original R12 FixedMul and original R12 flags; no R13 code compiled.' \
    'control: exact R12 Full, R14 feature flags disabled.' \
    'clip1: inline scalar first-match search for zero/one instead of memchr in R_ClipWallSegment.' \
    'clip2: two-byte unrolled first-match search, without unaligned word loads.' \
    'bbox: inline first-zero search instead of memchr in R_CheckBBox.' \
    'clip1bbox: both scalar clip and bbox; clip2bbox: unrolled clip and bbox.' \
    'Preflight tests compare all visible runs, solidcol changes, and bbox answers against baseline.' \
    'BlastEm: NTSC60, stock 68000 divider7, 1000% fast-forward, DEMO3 2134 frames. Repeat each 3x.' \
    'Reject variants with crashes, mismatched visuals, or gains smaller than repeatability noise.' \
    > "$dest/README.txt"
echo 'READY: R14 six ROMs'
