#!/usr/bin/env fish
# R6: compare Cache16 RAM, SRAM C, SRAM ASM, SRAM + 2/4 hot lines.
# Safe: separate checkout, no modifications to SGDK/runner/other projects.
set -l root (realpath (dirname (status filename))/../..)
cd $root; or exit 1
set -l outdir dist/r6-stable
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
set -lx DOOM_SRAM_CACHE16 0
set -lx DOOM_SRAM_FASTCOPY 0
set -lx DOOM_SRAM_HOT_SLOTS 0
set -lx DOOM_CACHE_STATS 0
python3 scripts/lab/test_ram_symbols.py; or exit 1

# Each experiment changes exactly its SRAM access strategy.
for variant in sramasm
    set DOOM_SRAM_CACHE16 1
    set DOOM_SRAM_FASTCOPY 1
    set DOOM_SRAM_HOT_SLOTS 0
    for mode in perf stats
        set DOOM_CACHE_STATS 0
        if test $mode = stats
            set DOOM_CACHE_STATS 1
        end
        set -lx DOOM_BUILD_ID "doom-md-r6stable-$variant-$mode"
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
        # Verify source variant was compiled (new feature macro appears in compiler options).
        if test "$DOOM_SRAM_CACHE16" = 1
            if not grep -q -- '-DDOOM_SRAM_CACHE16' "$outdir/build-$DOOM_BUILD_ID.log"
                echo "ERROR: SRAM compiler flag absent: $DOOM_BUILD_ID"
                exit 1
            end
        end
        if test "$DOOM_SRAM_FASTCOPY" = 1
            if not grep -q -- '-DDOOM_SRAM_FASTCOPY' "$outdir/build-$DOOM_BUILD_ID.log"
                echo "ERROR: assembly compiler flag absent: $DOOM_BUILD_ID"
                exit 1
            end
        end
        if test "$DOOM_SRAM_HOT_SLOTS" != 0
            if not grep -q -- "-DDOOM_SRAM_HOT_SLOTS=$DOOM_SRAM_HOT_SLOTS" "$outdir/build-$DOOM_BUILD_ID.log"
                echo "ERROR: hot-cache compiler flag absent: $DOOM_BUILD_ID"
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

printf '%s\n' \
    'R6 stable control: SRAM16 ASM; no hot-cache, no R7 optimizations.' \
    'Reference: 8.86 FPS, 2134 frames, 15685 hits, 5590 misses, 5574 evictions.' \
    'Static RAM free reference: 9276 bytes (subject to linker variations).' \
    'Keep 43KiB zone; compare both perf and stats in BlastEm 1.0.0.' \
    'If the baseline does not complete, stop and investigate before new changes.' \
    'Emulator only: SRAM writes can corrupt cartridge or flashcart save data.' \
    > "$outdir/README.txt"
python3 -c 'import pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1])
archive=root.parent/"doom-md-r6-stable-control.zip"
with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for f in sorted(root.iterdir()):
        if f.is_file(): z.write(f,f.name)
print("Created:",archive)
' "$outdir"; or exit 1
echo 'R6 stable control: 2 ROMs built.'
