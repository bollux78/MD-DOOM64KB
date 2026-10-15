#!/usr/bin/env fish
# Isolated 38x28 baseline vs 38x24+4-row black text HUD, Cache16 RAM only.
set -l root (realpath (dirname (status filename))/../..)
cd $root; or exit 1
set -l dest dist/classic-hud
mkdir -p $dest; or exit 1
set -l nm "$HOME/mars/m68k-elf/bin/m68k-elf-nm"
if set -q DOOM_MD_GDK
    set nm "$DOOM_MD_GDK/bin/m68k-elf-nm"
end

set -lx DOOM_TIMEDEMO 1
set -lx DOOM_NO_VSYNC 1
set -lx DOOM_FAST_DIVU 1
set -lx DOOM_CELL_LUT 1
set -lx DOOM_CACHE_SLOTS 16
set -lx DOOM_CACHE_STATS 0
set -lx DOOM_CLASSIC_TEXT_HUD 0

for variant in full28 hud24
    if test $variant = hud24
        set DOOM_CLASSIC_TEXT_HUD 1
    else
        set DOOM_CLASSIC_TEXT_HUD 0
    end
    for mode in perf stats
        if test $mode = stats
            set DOOM_CACHE_STATS 1
        else
            set DOOM_CACHE_STATS 0
        end
        set -lx DOOM_BUILD_ID "doom-md-hud-$variant-$mode"
        echo "Building $DOOM_BUILD_ID"
        fish scripts/build_silent.fish > "$dest/build-$DOOM_BUILD_ID.log" 2>&1
        if test $status -ne 0
            echo "Build failed: $DOOM_BUILD_ID"
            tail -n 80 "$dest/build-$DOOM_BUILD_ID.log"
            exit 1
        end
        if not test -s out/rom.bin; or not test -s out/release/rom.out
            echo "Missing ROM or ELF for $DOOM_BUILD_ID"
            exit 1
        end
        if test $variant = hud24
            if not grep -q -- '-DDOOM_CLASSIC_TEXT_HUD' "$dest/build-$DOOM_BUILD_ID.log"
                echo 'HUD macro missing from compiler command'
                exit 1
            end
        end
        python3 -c 'import pathlib,sys
b=pathlib.Path(sys.argv[1]).read_bytes()
ident=sys.argv[2]
assert len(b)>=0x200
assert b[0x120:0x150].decode("ascii").strip()==ident
assert b[0x150:0x180].decode("ascii").strip()==ident
' out/rom.bin "$DOOM_BUILD_ID"; or exit 1
        cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
        python3 scripts/lab/ram_usage.py \
            --elf out/release/rom.out \
            --nm "$nm" \
            --variant "$DOOM_BUILD_ID" \
            --fault-pc 0 \
            --output "$dest/ram-$DOOM_BUILD_ID.txt"; or exit 1
    end
end
printf '%s\n' \
    'Classic HUD experiment, no SRAM; original 68000 NTSC BlastEm 1.0.0.' \
    'full28: original 38x28 3D; hud24: 38x24 3D plus 4 rows black HUD.' \
    'Both physical display heights 28 rows for comparable picture layout.' \
    'Text bottom row shows HEALTH, ARMOR, BULLETS with values.' \
    'HUD rendering overhead in perf ROM is included in measurements.' \
    'Compare 2134 DEMO3 frames, do not infer FPS from area alone.' \
    'Cache stats may differ because reduced viewport changes rendering workload.' \
    'Experimental: compile and emulator-test before physical hardware.' \
    > "$dest/README.txt"
python3 -c 'import pathlib,sys,zipfile
d=pathlib.Path(sys.argv[1])
with zipfile.ZipFile(d.parent/"doom-md-classic-hud.zip","w",zipfile.ZIP_DEFLATED) as z:
 for p in sorted(d.iterdir()):
  if p.is_file(): z.write(p,p.name)
print("Created:",d.parent/"doom-md-classic-hud.zip")
' "$dest"; or exit 1
echo 'Classic HUD: 4 ROMs built.'
