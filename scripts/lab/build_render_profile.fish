#!/usr/bin/env fish
# HUD24 renderer profiling: identical build settings, sampling only in the profile ROM.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/render-profile
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
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_MASKED_DIVU 0
set -gx DOOM_RAM_STATS 0
set -gx DOOM_SRAM_CACHE16 0
set -gx DOOM_SRAM_FASTCOPY 0
set -e DOOM_ZONE_KIB

for variant in base r7
    set -gx DOOM_ROUTINE_PROFILE 0
    set -gx DOOM_R7_PROFILE 0
    switch $variant
        case base
            set -gx DOOM_BUILD_ID doom-md-hud-render-base
        case r7
            set -gx DOOM_ROUTINE_PROFILE 1
            set -gx DOOM_R7_PROFILE 1
            set -gx DOOM_BUILD_ID doom-md-hud-r7-profile
    end
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    echo "BUILD: $DOOM_BUILD_ID"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "ERROR: compile failed for $DOOM_BUILD_ID"
        tail -n 70 "$logfile"
        exit 1
    end
    test -s out/.render_options; or exit 1
    test -s out/rom.bin; or exit 1
    set -l flags (cat out/.render_options)
    for required in '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing compiler flag $required"
            exit 1
        end
    end
    if test $variant = base
        if string match -q -- '*-DDOOM_ROUTINE_PROFILE*' "$flags"
            echo 'ERROR: baseline accidentally profiled'
            exit 1
        end
    else
        string match -q -- '*-DDOOM_ROUTINE_PROFILE*' "$flags"; or begin
            echo 'ERROR: profiler not enabled'
            exit 1
        end
    end
    python3 -c 'import pathlib,sys
b=pathlib.Path("out/rom.bin").read_bytes()
name=sys.argv[1]
assert len(b)>=0x200 and len(b)<0x200000
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
    'HUD24 render profile: control vs VBlank sampling; 38x24 and status DMA, cache16 in WRAM.' \
    'base: expected approximately 9.39 FPS; compare new result with previous reference.' \
    'R7: 11 exclusive VBlank sampling categories, not cycle-exact.' \
    'Sample stages: OTHER/LOGIC, SETUP, BSP TRAVERSE (includes line prep), WALL COLUMNS (seg loop), MASKED/SPR, VDP WAIT/DMA.' \
    'These are broad stages, not function-level or cycle-accurate timing.' \
    'DEMO3 2134 frames, NTSC 60Hz, BlastEm 68000 divider 7.' \
    'No SRAM in either variant; performance control is uninstrumented.' \
    > "$dest/README.txt"
echo "READY: $dest"
