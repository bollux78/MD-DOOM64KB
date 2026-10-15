#!/usr/bin/env fish
# Round 5: build controlled zone-size experiments on the user's existing SGDK.
# Run at repository root: fish scripts/lab/run_round5.fish
# No emulator launches and NO writes to the shared SGDK toolchain.
set -l root (realpath (dirname (status filename))/../..)
cd $root; or exit 1
set -l outdir dist/round5
python3 scripts/lab/test_ram_symbols.py; or exit 1
mkdir -p $outdir; or exit 1

# Cache16 is the stability control; Cache32/64 are UNSAFE until diagnosed.
set -l configurations 16:43 16:39 32:43 32:41 32:39 64:39

set -lx DOOM_TIMEDEMO 1
set -lx DOOM_NO_VSYNC 1
set -lx DOOM_FAST_DIVU 1
set -lx DOOM_CELL_LUT 1
set -lx DOOM_FOLDED_TANGENT 0
set -lx DOOM_UNROLL_COLUMNS 0
set -lx DOOM_MASKED_DIVU 0
set -lx DOOM_CACHE8 0
set -lx DOOM_CACHE_STATS 0

for config in $configurations
    set -l parts (string split : $config)
    set -l slots $parts[1]
    set -l zone $parts[2]
    set -lx DOOM_CACHE_SLOTS $slots
    set -lx DOOM_ZONE_KIB $zone

    for mode in perf ram
        set -lx DOOM_BUILD_ID "doom-md-r5-c$slots-z$zone-$mode"
        if test $mode = ram
            set -lx DOOM_RAM_STATS 1
        else
            set -lx DOOM_RAM_STATS 0
        end
        echo "== Building $DOOM_BUILD_ID =="
        fish scripts/build_silent.fish > "$outdir/build-$DOOM_BUILD_ID.log" 2>&1
        if test $status -ne 0
            echo "Build failed. Last 60 lines of $outdir/build-$DOOM_BUILD_ID.log:"
            tail -n 60 "$outdir/build-$DOOM_BUILD_ID.log"
            exit 1
        end
        if not test -s out/rom.bin; or not test -s out/release/rom.out
            echo "Expected ROM or ELF missing: $DOOM_BUILD_ID"
            exit 1
        end
        # Fail closed on stale/mislabeled ROMs before sending to the lab.
        python3 -c 'import pathlib,sys
rom=pathlib.Path(sys.argv[1]).read_bytes()
expected=sys.argv[2]
assert len(rom)>=0x200, "ROM too short"
domestic=rom[0x120:0x150].decode("ascii").strip()
international=rom[0x150:0x180].decode("ascii").strip()
assert domestic==international==expected, (domestic,international,expected)
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
    'DOOM MD R5 - experimental zone-memory laboratory' \
    'BlastEm 1.0.0 / NTSC 60 Hz / 68000 divider 7 / DEMO3 2134 frames.' \
    'Default zone: 43 KiB; zone size variants: 43, 41, 39 KiB.' \
    'Use *-ram.bin to inspect ZONE PEAK USED, ZONE FREE NOW, STACK GAP SAMPLED.' \
    'Stack reading is only a sample, NOT a full stack high-water mark.' \
    '*-perf.bin contains no R5 diagnostic counters: only these results rank FPS.' \
    'Cache32 and Cache64 can crash/hang; emulator ONLY, never real hardware.' \
    'Do NOT assume reducing zone size is safe until full DEMO3 completes.' \
    'Send ram-*.txt, symbols-*.txt and screenshots of diagnostic ROMs.' \
    > "$outdir/README.txt"

python3 -c 'import pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1])
with zipfile.ZipFile(root.parent/"doom-md-round5-memory-lab.zip","w",zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.iterdir()):
        if p.is_file(): z.write(p,p.name)
print("Archive created:",root.parent/"doom-md-round5-memory-lab.zip")
' "$outdir"; or exit 1
echo "Round 5 complete."
