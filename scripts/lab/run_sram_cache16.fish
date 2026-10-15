#!/usr/bin/env fish
# R5 follow-up: identical Cache16 in work RAM versus cartridge SRAM.
# Usage: cd ~/Projetos/doom-md-sram; fish scripts/lab/run_sram_cache16.fish
set -l root (realpath (dirname (status filename))/../..)
cd $root; or exit 1
set -l outdir dist/sram-cache16
mkdir -p $outdir; or exit 1

python3 scripts/lab/test_ram_symbols.py; or exit 1
set -lx DOOM_TIMEDEMO 1
set -lx DOOM_NO_VSYNC 1
set -lx DOOM_FAST_DIVU 1
set -lx DOOM_CELL_LUT 1
set -lx DOOM_FOLDED_TANGENT 0
set -lx DOOM_UNROLL_COLUMNS 0
set -lx DOOM_MASKED_DIVU 0
set -lx DOOM_CACHE8 0
set -lx DOOM_CACHE_SLOTS 16
set -lx DOOM_CACHE_STATS 0
set -lx DOOM_RAM_STATS 0
set -lx DOOM_SRAM_CACHE16 0
set -lx DOOM_ZONE_KIB 43

for storage in ram sram
    if test $storage = sram
        set DOOM_SRAM_CACHE16 1
    else
        set DOOM_SRAM_CACHE16 0
    end
    for mode in perf stats
        if test $mode = stats
            set DOOM_CACHE_STATS 1
        else
            set DOOM_CACHE_STATS 0
        end
        set -lx DOOM_BUILD_ID "doom-md-r5-$storage"16"-$mode"
        echo "== Compiling $DOOM_BUILD_ID =="
        fish scripts/build_silent.fish > "$outdir/build-$DOOM_BUILD_ID.log" 2>&1
        if test $status -ne 0
            echo "Build failed; tail of log:"
            tail -n 70 "$outdir/build-$DOOM_BUILD_ID.log"
            exit 1
        end
        if not test -s out/rom.bin; or not test -s out/release/rom.out
            echo "Missing ROM or ELF: $DOOM_BUILD_ID"
            exit 1
        end
        if test $storage = sram
            if not grep -q -- '-DDOOM_SRAM_CACHE16' "$outdir/build-$DOOM_BUILD_ID.log"
                echo "Missing SRAM compile flag in $DOOM_BUILD_ID"
                exit 1
            end
        end
        python3 -c 'import pathlib,sys,struct
rom=pathlib.Path(sys.argv[1]).read_bytes()
ident=sys.argv[2]
assert len(rom)<0x200000, "ROM overlaps cartridge SRAM mapping"
assert len(rom)>=0x200
assert rom[0x120:0x150].decode("ascii").strip()==ident
assert rom[0x150:0x180].decode("ascii").strip()==ident
assert rom[0x1B0:0x1B2]==b"RA", "No SRAM signature in ROM header"
start,end=struct.unpack_from(">II",rom,0x1B4)[0],struct.unpack_from(">II",rom,0x1B8)[0]
assert start==0x200000 and end==0x20FFFF, (hex(start),hex(end))
' out/rom.bin "$DOOM_BUILD_ID"; or exit 1
        cp out/rom.bin "$outdir/$DOOM_BUILD_ID.bin"; or exit 1
        python3 scripts/lab/ram_usage.py \
            --elf out/release/rom.out \
            --nm "$HOME/mars/m68k-elf/bin/m68k-elf-nm" \
            --variant "$DOOM_BUILD_ID" \
            --output "$outdir/ram-$DOOM_BUILD_ID.txt"; or exit 1
        python3 scripts/lab/ram_symbols.py \
            --elf out/release/rom.out \
            --nm "$HOME/mars/m68k-elf/bin/m68k-elf-nm" \
            --variant "$DOOM_BUILD_ID" \
            --output "$outdir/symbols-$DOOM_BUILD_ID.txt"; or exit 1
    end
end

printf '%s\n' \
    'Cache16 SRAM experiment: same 43 KiB Doom zone, 16 slots, identical rendering flags.' \
    'RAM: normal 2048-byte contiguous column cache.' \
    'SRAM: 2048-byte 8-bit odd-lane cartridge SRAM; 128-byte work RAM staging.' \
    'SRAM mode copies each column to SRAM on miss and from SRAM on hit.' \
    'ROM SRAM signature and range checked. Emulator SRAM support required.' \
    'Run in BlastEm 1.0.0 only; DO NOT test on physical cartridge/flashcart.' \
    'Use perf ROMs for FPS. Stats ROMs measure hits/misses with overhead.' \
    'If SRAM init fails, the ROM displays SRAM NOT FOUND and stops.' \
    'DEMO3: NTSC 60Hz, 68000 divider 7, 2134 frames.' \
    > "$outdir/README.txt"

python3 -c 'import pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1])
dest=root.parent/"doom-md-r5-sram-cache16.zip"
with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.iterdir()):
        if p.is_file(): z.write(p,p.name)
print("Created:",dest)
' "$outdir"; or exit 1
echo "SRAM Cache16 experiment compiled."
