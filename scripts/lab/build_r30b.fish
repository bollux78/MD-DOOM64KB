#!/usr/bin/env fish
# R25: Episode 1 soundtrack; paired legacy controls plus music 8x8/4x4.
# Base of EVERY ROM = R20h common flags + vc-all (V3, ROM color, R5, cache
# direct, R6, M2), natural inlining. Each variant adds DOOM_R21_* blocks (and,
# for the stability probes, the old R20 S5/V2 flags) from r21_matrix.json.
# Compare FPS only against doom-md-r21-control; hash/diag/cnt/prof ROMs carry
# instrumentation overhead and answer other questions (see docs/review-r21).
# Usage: fish scripts/lab/build_r21.fish [variant ...]
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r30b
mkdir -p "$dest"; or exit 1

set -l variants native-control-play bayer4-play bayer4-perf bayer8-play bayer8-perf
if test (count $argv) -gt 0
    set variants $argv
end
for v in $variants
    contains -- $v native-control-play bayer4-play bayer4-perf bayer8-play bayer8-perf; or exit 2
end
python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r15_wallmul.py; or exit 1
python3 scripts/lab/test_r16_crt_hud.py; or exit 1
python3 scripts/lab/test_r17_pixel_loop.py; or exit 1
python3 scripts/lab/gen_r12_recip_lut.py --max-scale 65535; or exit 1
python3 scripts/lab/gen_r22_pixel4.py; or exit 1
python3 scripts/lab/test_r22_pixel4.py; or exit 1

# Same proven R18 renderer flags as build_r19_timedemo.fish.
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
set -gx DOOM_R9_SLOPE_DIVU 1
set -gx DOOM_R9_STEP_DIVS 1
set -gx DOOM_R10_DIST_DIVU 1
set -gx DOOM_R10_RECIP_DIVU 0
set -gx DOOM_R12_RECIP_LUT 65535
set -gx DOOM_R12_RECIP_MASKED 0
set -e DOOM_R13_MUL_DECOMP
set -e DOOM_R14_CLIPSCAN
set -e DOOM_R14_BBOXSCAN
set -gx DOOM_FOLDED_TANGENT 0
set -gx DOOM_UNROLL_COLUMNS 0
set -gx DOOM_MASKED_DIVU 0
set -gx DOOM_RAM_STATS 0
set -gx DOOM_SRAM_CACHE16 0
set -gx DOOM_SRAM_FASTCOPY 0
set -gx DOOM_R8_LUT_UNROLL 0
set -gx DOOM_R8_SKIP_MASKED_RECIP 0
set -gx DOOM_R11_TOPBAR_CLIP 1
set -gx DOOM_R11_TOPBAR_DMA 0
set -gx DOOM_R11_LEFTCOL_CLIP 1
set -e DOOM_ZONE_KIB
set -gx DOOM_R15_TANMUL 0
set -gx DOOM_R15_SETUPMUL 1
set -gx DOOM_R16_HUD_UP2 1
set -gx DOOM_R16_WEAPON_LIFT 1
set -gx DOOM_R17_PIXEL_DBRA 1
set -gx DOOM_R17_FRAC_MULU 0
set -gx DOOM_R19_FLAT_DBRA 1

# Music: same E1M1 VGM as R19, unless explicitly disabled.
rm -f res/music.rs res/music.d
if set -q DOOM_R20_NO_MUSIC; and test "$DOOM_R20_NO_MUSIC" = 1
    rm -f res/e1m1.vgm   # build_silent.fish recreates a silent placeholder
    echo 'NOTE: DOOM_R20_NO_MUSIC=1, silent placeholder VGM'
else
    set -l music "$HOME/Projetos/doom-assets/e1m1.vgm"
    if set -q DOOM_R20_BGM_VGM
        set music "$DOOM_R20_BGM_VGM"
    end
    if not test -s "$music"
        echo "ERROR: E1M1 VGM not found: $music (or set DOOM_R20_NO_MUSIC=1)"
        exit 2
    end
    python3 scripts/lab/check_r18_vgm.py "$music"; or exit 1
    if test (realpath "$music") != (realpath -m "$root/res/e1m1.vgm")
        cp -- "$music" "$root/res/e1m1.vgm"; or exit 1
    end
end

set -l control '-DDOOM_R20_SIGHT_ITERATIVE' '-DDOOM_R20_PIXEL_ADDX' '-DDOOM_R20_TAN_MULS' '-DDOOM_R20_CELLMAP_MEMO' '-DDOOM_R20_HUD_LAZY' '-DDOOM_R20_FPS_LAZY' '-DDOOM_R20_SCALE_MATH' '-DDOOM_R20_BSP_ITERATIVE' '-DDOOM_R20_DMA_BATCH' '-DDOOM_R20_COLOR_ROM' '-DDOOM_R20_REG_COLUMNS' '-DDOOM_R20_CACHE_DIRECT' '-DDOOM_R20_FLAT_INLINE' '-DDOOM_R20_TAN32' '-DDOOM_R20_VBLANK_VIDEO' '-DDOOM_R21_V2_HEAPBUF' '-DDOOM_R21_NO_VDP_INIT'
set -l pixel '-DDOOM_R20_SIGHT_ITERATIVE' '-DDOOM_R20_TAN_MULS' '-DDOOM_R20_SCALE_MATH' '-DDOOM_R20_BSP_ITERATIVE' '-DDOOM_R20_DMA_BATCH' '-DDOOM_R20_CACHE_DIRECT' '-DDOOM_R20_TAN32' '-DDOOM_R20_VBLANK_VIDEO' '-DDOOM_R21_NO_VDP_INIT'
cp scripts/doom64.wad /tmp/r23-original.wad; or exit 1
function r23_restore_wad --on-event fish_exit
    cp /tmp/r23-original.wad scripts/doom64.wad
end
python3 scripts/lab/convert_r24_episode.py --payload assets/r24-episode.json --base /tmp/r23-original.wad --out /tmp/r23-converted.wad --report "$dest/map-report.json" --header src/r24_static_types.h; or exit 1
# Each variant regenerates ONLY the static art (no changes to gameplay/rendering).
# R30 native control uses precisely the old no-dither pixels and palette banks.
set -l built
for v in $variants
    set -gx DOOM_R29_XGM2 1
    set -gx DOOM_R29_MULTI 1
    set -gx DOOM_R30_NATIVE 1
    set -gx DOOM_R22_PIXEL4 0
    set -gx DOOM_R27_SINGLE_TRACK 0
    set -gx DOOM_R25_MUSIC 0
    set -gx DOOM_WAD_DEDUP 0
    set -gx DOOM_TIMEDEMO 1
    set -gx DOOM_CELL_LUT 1
    set -gx DOOM_R17_PIXEL_DBRA 1
    set -gx DOOM_R19_FLAT_DBRA 1
    set -gx DOOM_R16_WEAPON_LIFT 1
    set -l defs $control
    if test "$v" = episode-p4
        set -gx DOOM_R22_PIXEL4 1
        set -gx DOOM_CELL_LUT 0
        set -gx DOOM_R17_PIXEL_DBRA 0
        set -gx DOOM_R19_FLAT_DBRA 0
        set -gx DOOM_R16_WEAPON_LIFT 2
        set defs $pixel '-DDOOM_R22_SOLID_TILES' '-DDOOM_R22_PAIR_LUT'
    end
    set defs $defs '-DDOOM_R22_SRAM_BLOCKLINKS' '-DDOOM_R26_FLOW' 
    if contains -- $v native-control-play bayer4-play bayer8-play
        set -gx DOOM_TIMEDEMO 0
    end
    if not contains -- $v control play-control
        set defs $defs '-DDOOM_R23_MAPMEM' '-DDOOM_R24_EPISODE' '-DDOOM_R25_MUSIC'
        set -gx DOOM_R25_MUSIC 1
        set -gx DOOM_WAD_DEDUP 1
    end
    if contains -- $v direct-e1m2 diag-e1m2 direct-p4
        set defs $defs '-DDOOM_R23_MAP2_DIRECT'
    end
    if contains -- $v cpu-base cpu-group cpu-fixed cpu-lowgroup
        set defs $defs '-DDOOM_R22_MAP_DIAG'
    end
    if contains -- $v cpu-base cpu-group cpu-fixed cpu-lowgroup
        set defs $defs '-DDOOM_R23_CPU_PROBE' '-DDOOM_R27_RENDER_PROBE'
    end
    if contains -- $v low-window low-fixed low-group low-play cpu-fixed cpu-lowgroup xgm2-low-fixed xgm2-low-group
        set -gx DOOM_R27_SINGLE_TRACK 1
        set defs $defs '-DDOOM_R27_SINGLE_TRACK'
    end
    if contains -- $v low-fixed low-group low-play cpu-fixed cpu-lowgroup xgm2-low-fixed xgm2-low-group
        set defs $defs '-DDOOM_R27_SRAM_FIXED'
    end
    if contains -- $v native-control-play bayer4-play bayer4-perf bayer8-play bayer8-perf
        set defs $defs '-DDOOM_R27_GROUP_SIDE'
    end
    if contains -- $v native-control-play bayer4-play bayer4-perf bayer8-play bayer8-perf
        set defs $defs '-DDOOM_R27_GROUP_LINE'
    end
    if not contains -- $v cpu-base cpu-group cpu-fixed cpu-lowgroup
        set defs $defs '-DDOOM_R28_VIDEO_AUDIT'
    end
    set -l dither none
    if string match -q 'bayer4-*' -- "$v"
        set dither bayer4
    else if string match -q 'bayer8-*' -- "$v"
        set dither bayer8
    end
    # The native art generator reads SOURCE bitmaps; this copy ensures it
    # cannot accidentally read the converted/stripped WAD of the last build.
    cp /tmp/r23-original.wad scripts/doom64.wad; or exit 1
    python3 scripts/lab/gen_r30_native.py --dither "$dither" > "$dest/art-$v.json"; or exit 1
    # Doom game uses the episode-converted WAD. Original 240x160 bitmaps
    # are omitted by repack_wad in R30_NATIVE variants.
    cp /tmp/r23-converted.wad scripts/doom64.wad; or exit 1
    python3 scripts/lab/prepare_r25_music.py; or exit 1
    if test "$DOOM_R29_XGM2" = 1
        set defs $defs '-DDOOM_R29_XGM2'
    end
    if test "$DOOM_R29_MULTI" = 1
        set defs $defs '-DDOOM_R29_MULTI'
    end
    if test "$DOOM_R30_NATIVE" = 1
        set defs $defs '-DDOOM_R30_NATIVE'
    end
    set -gx DOOM_R20_DEFINES (string join ' ' -- $defs)
    set -l id doom-md-r30b-$v
    set -gx DOOM_BUILD_ID $id
    echo "BUILD: $id  [$DOOM_R20_DEFINES]"
    rm -rf out
    rm -f res/music.rs res/music.d
    # Explicit env boundary: preserve flags across nested fish interpreter.
    env DOOM_R20_DEFINES="$DOOM_R20_DEFINES" fish scripts/build_silent.fish > "$dest/build-$id.log" 2>&1
    or begin
        tail -n 100 "$dest/build-$id.log"
        exit 1
    end
    cp out/rom.bin "$dest/$id.bin"; or exit 1
    cp out/release/rom.out "$dest/$id.elf"; or exit 1
    cp out/.render_options "$dest/flags-$id.txt"; or exit 1
    set built $built $id
end
cp /tmp/r23-original.wad scripts/doom64.wad; or exit 1
python3 scripts/lab/audit_r30b.py "$dest" $variants; or exit 1
sha256sum $dest/*.bin > "$dest/SHA256SUMS"
echo "READY: R30b adaptive Bayer native H40 static screens with matched R30 control; emulator/hardware validation pending"
