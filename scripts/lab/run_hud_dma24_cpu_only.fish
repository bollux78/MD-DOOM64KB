#!/usr/bin/env fish
# One ROM only: isolate 24-row DMA + CPU-updated HUD from failed multi-DMA.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/hud-dma24-cpu
mkdir -p "$dest"; or exit 1

# Export explicitly in the function/global scope; never set -lx inside if.
set -gx DOOM_TIMEDEMO 1
set -gx DOOM_NO_VSYNC 1
set -gx DOOM_FAST_DIVU 1
set -gx DOOM_CELL_LUT 1
set -gx DOOM_CACHE_SLOTS 16
set -gx DOOM_CACHE_STATS 0
set -gx DOOM_CLASSIC_TEXT_HUD 1
set -gx DOOM_HUD_DMA24 1
set -gx DOOM_BUILD_ID doom-md-dma24cpu-perf

echo "Building $DOOM_BUILD_ID (24 rows DMA + HUD CPU)"
fish scripts/build_silent.fish > "$dest/build-$DOOM_BUILD_ID.log" 2>&1
if test $status -ne 0
    echo "FAILED: compiler. Last 40 log lines:"
    tail -n 40 "$dest/build-$DOOM_BUILD_ID.log"
    exit 1
end

if not grep -q -- '-DDOOM_HUD_DMA24' "$dest/build-$DOOM_BUILD_ID.log"
    echo "FAILED: DMA24 flag did not reach compiler."
    exit 1
end
if not grep -q -- '-DDOOM_CLASSIC_TEXT_HUD' "$dest/build-$DOOM_BUILD_ID.log"
    echo "FAILED: HUD24 flag did not reach compiler."
    exit 1
end
if not test -s out/rom.bin
    echo "FAILED: no binary produced"
    exit 1
end

python3 -c 'import pathlib
b=pathlib.Path("out/rom.bin").read_bytes()
s="doom-md-dma24cpu-perf"
assert b[0x120:0x150].decode("ascii").strip()==s
assert b[0x150:0x180].decode("ascii").strip()==s
print("Verified ROM ID:",s)
'; or exit 1
cp out/rom.bin "$dest/doom-md-dma24cpu-perf.bin"; or exit 1
echo "SUCCESS: $dest/doom-md-dma24cpu-perf.bin"
echo "Test ONLY this experimental ROM in BlastEm, not on cartridge."
