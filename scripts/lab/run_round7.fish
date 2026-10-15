#!/usr/bin/env fish
# R7: SRAM ASM baseline vs 4x DBRA unroll vs fixed 64/128-byte paths.
# Safe: separate checkout, no modifications to SGDK/runner/other projects.
set -l root (realpath (dirname (status filename))/../..)
cd $root; or exit 1
set -l outdir dist/round7
mkdir -p $outdir; or exit 1
set -l nm "$HOME/mars/m68k-elf/bin/m68k-elf-nm"
if set -q DOOM_MD_GDK
    set nm "$DOOM_MD_GDK/bin/m68k-elf-nm"
end
set -lx DOOM_TIMEDEMO 1
set -lx DOOM_NO_VSYNC 1
set -lx DOOM_FAST_DIVU 1
set -lx DOOM_CELL_LUT 1
set -lx DOOM_FOLDED_TANGENT 0
set -lx DOOM_UNROLL_COLUMNS 0
set -lx DOOM_MASKED_DIVU 0
set -lx DOOM_CACHE8 0
set -lx DOOM_CACHE_SLOTS 16
set -lx DOOM_RAM_STATS 0
set -lx DOOM_ZONE_KIB 43
set -lx DOOM_SRAM_CACHE16 1
set -lx DOOM_SRAM_FASTCOPY 1
set -lx DOOM_SRAM_HOT_SLOTS 0
set -lx DOOM_SRAM_UNROLL4 0
set -lx DOOM_SRAM_SPECIAL128 0
set -lx DOOM_CACHE_STATS 0
python3 scripts/lab/test_ram_symbols.py; or exit 1

# Each experiment changes exactly its SRAM access strategy.
for variant in asm unroll4 fixed128
    set DOOM_SRAM_UNROLL4 0
    set DOOM_SRAM_SPECIAL128 0
    switch $variant
        case asm
        case unroll4
            set DOOM_SRAM_UNROLL4 1
        case fixed128
            set DOOM_SRAM_UNROLL4 1
            set DOOM_SRAM_SPECIAL128 1
    end
    for mode in perf stats
        set DOOM_CACHE_STATS 0
        if test $mode = stats
            set DOOM_CACHE_STATS 1
        end
        set -lx DOOM_BUILD_ID "doom-md-r7-$variant-$mode"
        echo "R6 compiling $DOOM_BUILD_ID"
        fish scripts/build_silent.fish > "$outdir/build-$DOOM_BUILD_ID.log" 2>&1
        if test $status -ne 0
            echo "Build failed for $DOOM_BUILD_ID"
            tail -n 70 "$outdir/build-$DOOM_BUILD_ID.log"
            exit 1
        end
        if not test -s out/rom.bin; or not test -s out/release/rom.out
            echo "Missing ROM or ELF for $DOOM_BUILD_ID"
            exit 1
        end
        for flag in DOOM_SRAM_CACHE16 DOOM_SRAM_FASTCOPY
            if not grep -q -- "-D$flag" "$outdir/build-$DOOM_BUILD_ID.log"
                echo "ERROR: Missing $flag for $DOOM_BUILD_ID"
                exit 1
            end
        end
        if test "$DOOM_SRAM_UNROLL4" = 1
            if not grep -q -- '-DDOOM_SRAM_UNROLL4' "$outdir/build-$DOOM_BUILD_ID.log"
                echo "ERROR: missing unroll4 flag"
                exit 1
            end
        end
        if test "$DOOM_SRAM_SPECIAL128" = 1
            if not grep -q -- '-DDOOM_SRAM_SPECIAL128' "$outdir/build-$DOOM_BUILD_ID.log"
                echo "ERROR: missing specialized flag"
                exit 1
            end
        end
        python3 -c 'import pathlib,sys,struct
rom=pathlib.Path(sys.argv[1]).read_bytes()
ident=sys.argv[2]
assert len(rom)<0x200000, "ROM overlaps SRAM window"
assert len(rom)>=0x200
assert rom[0x120:0x150].decode("ascii").strip()==ident
assert rom[0x150:0x180].decode("ascii").strip()==ident
assert rom[0x1B0:0x1B2]==b"RA"
assert struct.unpack_from(">II",rom,0x1B4)==(0x200000,0x20FFFF)
' out/rom.bin "$DOOM_BUILD_ID"; or exit 1
        cp out/rom.bin "$outdir/$DOOM_BUILD_ID.bin"; or exit 1
        python3 scripts/lab/ram_usage.py \
            --elf out/release/rom.out \
            --nm "$nm" \
            --variant "$DOOM_BUILD_ID" \
            --output "$outdir/ram-$DOOM_BUILD_ID.txt"; or exit 1
        python3 scripts/lab/ram_symbols.py \
            --elf out/release/rom.out \
            --nm "$nm" \
            --variant "$DOOM_BUILD_ID" \
            --output "$outdir/symbols-$DOOM_BUILD_ID.txt"; or exit 1
    end
end

printf '%s\\n' \\
    'R7 SRAM copy optimization experiment (all use 16 SRAM cache slots).' \\
    'asm: Round 6 proven scalar DBRA copy reference.' \\
    'unroll4: four SRAM byte transfers per DBRA iteration.' \\
    'fixed128: unroll4 with specialized constant-count paths for 64/128 bytes.' \\
    '43KiB Doom zone, DEMO3 2134 frames, NTSC 60Hz, divider 7.' \\
    'Use PERF for FPS; STATS should match 15685 hits, 5590 misses, 5574 evictions.' \\
    'BlastEm 1.0.0 only; cartridge SRAM mapping must be enabled.' \\
    'Not suitable for real hardware or flashcart without SRAM compatibility review.' \\
    > "$outdir/README.txt"
python3 -c 'import pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1])
archive=root.parent/"doom-md-r7-sram-copy.zip"
with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted(root.iterdir()):
        if f.is_file(): z.write(f,f.name)
print("Created:",archive)
' "$outdir"; or exit 1
echo 'R7 6 ROM matrix completed.'
