#!/usr/bin/env fish
# Controlled HUD24 reference versus HUD24 with 24-row-only gameplay DMA.
set -l root (realpath (dirname (status filename))/../..)
cd $root; or exit 1
set -l dest dist/hud-dma24
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
set -gx DOOM_HUD_DMA24 0

for variant in hud24 dma24
    set DOOM_CLASSIC_TEXT_HUD 1
    if test $variant = dma24
        set -gx DOOM_HUD_DMA24 1
    else
        set -gx DOOM_HUD_DMA24 0
    end
    for mode in perf stats
        if test $mode = stats
            set DOOM_CACHE_STATS 1
        else
            set DOOM_CACHE_STATS 0
        end
        set -lx DOOM_BUILD_ID "doom-md-dma-$variant-$mode"
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
        # Validate exactly which feature macro reached the compiler.
        if test $variant = dma24
            if not grep -q -- '-DDOOM_HUD_DMA24' "$dest/build-$DOOM_BUILD_ID.log"
                echo 'ERROR: DMA24 macro did not reach the compiler'
                exit 1
            end
        else
            if grep -q -- '-DDOOM_HUD_DMA24' "$dest/build-$DOOM_BUILD_ID.log"
                echo 'ERROR: baseline was compiled with DMA24 enabled'
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
    'DMA24 isolated experiment: HUD 38x24 old full 28-row DMA vs split.' \
    'hud24: original stable classic text HUD, DMA 28 rows each frame.' \
    'dma24: DMA 24 3D rows each frame; copy changed HUD tilemap rows only.' \
    'Both have the same 24-row 3D renderer and same HUD content.' \
    'Compare DEMO3 2134 frames and ensure the black strip remains visible.' \
    'Do not merge until both PERF and STATS pass BlastEm.' \
    > "$dest/README.txt"
python3 -c 'import pathlib,sys,zipfile
d=pathlib.Path(sys.argv[1])
with zipfile.ZipFile(d.parent/"doom-md-hud-dma24.zip","w",zipfile.ZIP_DEFLATED) as z:
 for p in sorted(d.iterdir()):
  if p.is_file(): z.write(p,p.name)
print("Created:",d.parent/"doom-md-hud-dma24.zip")
' "$dest"; or exit 1
echo 'HUD DMA24: 4 ROMs built.'
