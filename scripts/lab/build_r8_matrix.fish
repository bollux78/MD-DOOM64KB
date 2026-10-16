#!/usr/bin/env fish
# R8: performance matrix for HUD24. No instrumentation; preserve R7 and baseline.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r8
mkdir -p "$dest"; or exit 1

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
set -e DOOM_ZONE_KIB

for variant in base lut2 lut4 masked combo4
    set -gx DOOM_R8_LUT_UNROLL 0
    set -gx DOOM_R8_SKIP_MASKED_RECIP 0
    switch $variant
        case base
            set -gx DOOM_BUILD_ID doom-md-hud-r8-base
        case lut2
            set -gx DOOM_R8_LUT_UNROLL 2
            set -gx DOOM_BUILD_ID doom-md-hud-r8-lut2
        case lut4
            set -gx DOOM_R8_LUT_UNROLL 4
            set -gx DOOM_BUILD_ID doom-md-hud-r8-lut4
        case masked
            set -gx DOOM_R8_SKIP_MASKED_RECIP 1
            set -gx DOOM_BUILD_ID doom-md-hud-r8-masked
        case combo4
            set -gx DOOM_R8_LUT_UNROLL 4
            set -gx DOOM_R8_SKIP_MASKED_RECIP 1
            set -gx DOOM_BUILD_ID doom-md-hud-r8-combo4
    end
    echo "BUILD: $DOOM_BUILD_ID"
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "ERROR: build failed $DOOM_BUILD_ID"
        tail -n 80 "$logfile"
        exit 1
    end
    test -s out/rom.bin; or exit 1
    test -s out/.render_options; or exit 1
    set -l flags (cat out/.render_options)
    for required in '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing expected compiler flag $required"
            exit 1
        end
    end
    if string match -q -- '*-DDOOM_ROUTINE_PROFILE*' "$flags"; or string match -q -- '*-DDOOM_R7_PROFILE*' "$flags"; or string match -q -- '*-DDOOM_SRAM_CACHE16*' "$flags"
        echo 'ERROR: polluted performance control'
        exit 1
    end
    if test $DOOM_R8_LUT_UNROLL -eq 0
        if string match -q -- '*-DDOOM_R8_LUT_UNROLL*' "$flags"
            echo 'ERROR: unexpected LUT unroll'
            exit 1
        end
    else
        string match -q -- "*-DDOOM_R8_LUT_UNROLL=$DOOM_R8_LUT_UNROLL*" "$flags"; or exit 1
    end
    if test $DOOM_R8_SKIP_MASKED_RECIP -eq 1
        string match -q -- '*-DDOOM_R8_SKIP_MASKED_RECIP*' "$flags"; or exit 1
    else if string match -q -- '*-DDOOM_R8_SKIP_MASKED_RECIP*' "$flags"
        echo 'ERROR: unexpected mask shortcut'
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
    if test -s out/release/rom.out
        cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
    end
    cp out/.render_options "$dest/flags-$DOOM_BUILD_ID.txt"; or exit 1
end
printf '%s\n' \
    'R8 HUD24 38x24 timedemo, DEMO3 2134 frames NTSC60, BlastEm divider=7.' \
    'Compare FIVE uninstrumented ROMs from this artifact.' \
    'base: reference expected 9.39 FPS.' \
    'lut2/lut4: 2 or 4 pixels/loop only in fast Color LUT path.' \
    'masked: skip wall fracstep calculation when only a masked midtexture is present.' \
    'combo4: lut4 + masked, tests interactions.' \
    'Exact texture indices, 16-bit frac wrap, clipping, HUD DMA, palette and WRAM cache preserved.' \
    'Verify screenshots and DEMO3 2134 frames before accepting performance changes.' \
    'Benchmark BlastEm at 1000% with divider=7. Do not compare ASM 68030/68060 routines.' \
    'Research: github.com/FrenkelS/Doom8088 ; github.com/zz964/x68D00M ; gendev.spritesmind.net/forum/viewtopic.php?t=2598' \
    > "$dest/README.txt"
echo "READY: five R8 ROMs in $dest"
