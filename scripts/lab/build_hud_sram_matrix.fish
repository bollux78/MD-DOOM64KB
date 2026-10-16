#!/usr/bin/env fish
# HUD24 controlled experiment: Cache16 WRAM reference vs cartridge SRAM C / ASM.
# Uses the same 38x24 viewport, status-only DMA, palette, WAD, and no profiling.
# Compile three reference-identifiable ROMs; never overwrite the canonical HUD file.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/hud-sram
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
set -gx DOOM_ROUTINE_PROFILE 0
set -gx DOOM_PROFILE 0
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_MASKED_DIVU 0
set -gx DOOM_RAM_STATS 0
set -gx DOOM_SRAM_CACHE16 0
set -gx DOOM_SRAM_FASTCOPY 0
set -e DOOM_ZONE_KIB

for variant in ram sramc sramasm
    set -gx DOOM_SRAM_CACHE16 0
    set -gx DOOM_SRAM_FASTCOPY 0
    switch $variant
        case ram
            set -gx DOOM_BUILD_ID doom-md-hudstatus-perf
        case sramc
            set -gx DOOM_SRAM_CACHE16 1
            set -gx DOOM_BUILD_ID doom-md-hud-sramc-perf
        case sramasm
            set -gx DOOM_SRAM_CACHE16 1
            set -gx DOOM_SRAM_FASTCOPY 1
            set -gx DOOM_BUILD_ID doom-md-hud-sramasm-perf
    end
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    echo "BUILD: $DOOM_BUILD_ID"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "ERROR: compile failed for $DOOM_BUILD_ID"
        tail -n 70 "$logfile"
        exit 1
    end
    if not test -s out/.render_options; or not test -s out/rom.bin
        echo 'ERROR: missing compile stamp or ROM'
        exit 1
    end
    set -l flags (cat out/.render_options)
    if not string match -q -- "*$DOOM_BUILD_ID" "$flags"
        echo "ERROR: stamp does not match ROM variant: $flags"
        exit 1
    end
    for required in '-DVIEWWINDOWHEIGHT=24' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DTIMEDEMO' '-DDOOM_NO_VSYNC'
        if not string match -q -- "*$required*" "$flags"
            echo "ERROR: missing expected compiler flag $required"
            exit 1
        end
    end
    if test $variant = ram
        if string match -q -- '*-DDOOM_SRAM_CACHE16*' "$flags"; or string match -q -- '*-DDOOM_SRAM_FASTCOPY*' "$flags"
            echo "ERROR: RAM reference contains an SRAM flag"
            exit 1
        end
    else
        if not string match -q -- '*-DDOOM_SRAM_CACHE16*' "$flags"
            echo "ERROR: SRAM option not active"
            exit 1
        end
        if test $variant = sramasm
            if not string match -q -- '*-DDOOM_SRAM_FASTCOPY*' "$flags"
                echo "ERROR: ASM flag not active"
                exit 1
            end
        else if string match -q -- '*-DDOOM_SRAM_FASTCOPY*' "$flags"
            echo "ERROR: SRAM C incorrectly has ASM option"
            exit 1
        end
    end
    python3 -c 'import pathlib,sys,struct
b=pathlib.Path("out/rom.bin").read_bytes()
name=sys.argv[1]; variant=sys.argv[2]
assert len(b)>=0x200 and len(b)<0x200000
assert b[0x120:0x150].decode("ascii").strip()==name
assert b[0x150:0x180].decode("ascii").strip()==name
if variant!="ram":
    assert b[0x1b0:0x1b2]==b"RA"
    assert struct.unpack_from(">II",b,0x1b4)==(0x200000,0x20ffff)
print("VERIFIED:",name,len(b),"bytes")
' "$DOOM_BUILD_ID" "$variant"; or exit 1
    cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
    if test -s out/release/rom.out
        cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
    end
    cp out/.render_options "$dest/flags-$DOOM_BUILD_ID.txt"; or exit 1
end
printf '%s\n' \
    'HUD SRAM test matrix, 38x24 3D + 4 rows text HUD, conditional 24/28-row DMA.' \
    'ram:      doom-md-hudstatus-perf.bin; reference expected about 9.39 FPS.' \
    'sramc:    doom-md-hud-sramc-perf.bin; unknown FPS.' \
    'sramasm:  doom-md-hud-sramasm-perf.bin; unknown FPS.' \
    'DEMO3 2134 frames; NTSC 60Hz; stock 68000 speed (BlastEm divider 7).' \
    'Use BlastEm 1.0.0 with cartridge odd-lane SRAM enabled.' \
    'SRAM variants test write access and show ERROR if SRAM unavailable.' \
    'EMULATOR EXPERIMENT ONLY: original hardware/flashcart not verified.' \
    'Always compare all 3 builds from this same commit. No FPS claims until measured.' \
    > "$dest/README.txt"
echo "READY: $dest (3 ROMs)"
