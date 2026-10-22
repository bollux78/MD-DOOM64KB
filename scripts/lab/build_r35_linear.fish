#!/usr/bin/env fish
# R35: 4 MiB linear cartridge, no new codecs, raw Bayer8 static artwork.
# Four ROMs: cell (R31 gameplay) and pixel4 (R22), playable and timedemo.
# Base of EVERY ROM = R20h common flags + vc-all (V3, ROM color, R5, cache
# direct, R6, M2), natural inlining. Each variant adds DOOM_R21_* blocks (and,
# for the stability probes, the old R20 S5/V2 flags) from r21_matrix.json.
# Compare FPS only against doom-md-r21-control; hash/diag/cnt/prof ROMs carry
# instrumentation overhead and answer other questions (see docs/review-r21).
# Usage: fish scripts/lab/build_r21.fish [variant ...]
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r35
mkdir -p "$dest"; or exit 1

set -l variants cell-play cell-perf pixel4-play pixel4-perf
if test (count $argv) -gt 0
    set variants $argv
end
for v in $variants
    contains -- $v cell-play cell-perf cell-profperf pixel4-play pixel4-perf; or exit 2
end
python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r15_wallmul.py; or exit 1
python3 scripts/lab/test_r16_crt_hud.py; or exit 1
python3 scripts/lab/test_r17_pixel_loop.py; or exit 1
python3 scripts/lab/gen_r12_recip_lut.py --max-scale 65535; or exit 1
python3 scripts/lab/gen_r22_pixel4.py; or exit 1
if test "$DOOM_R49_COLORMIX" = 1; or test "$DOOM_R49_COMPLUT" = 1
    # Pure ROM tables: color fidelity gate and/or precomposed colormap.
    python3 scripts/lab/gen_r49_colormix.py; or exit 1
end
if set -q DOOM_R52_AB; and test "$DOOM_R52_AB" = 1
    if set -q DOOM_R52_CLAUDIO; and test "$DOOM_R52_CLAUDIO" = 1
        python3 scripts/lab/gen_r52_claudio.py --repo . --out src --mode "$DOOM_R52_AB_PROFILE" --zero-policy "$DOOM_R52_ZERO_POLICY" --no-preview; or exit 1
        python3 scripts/lab/test_r52_claudio.py src .; or exit 1
    else
        python3 scripts/lab/gen_r52_ab.py --profile "$DOOM_R52_AB_PROFILE"; or exit 1
    end
end
python3 scripts/lab/gen_r43_gray.py; or exit 1
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
    if string match -q 'pixel4-*' -- "$v"
        set -gx DOOM_R22_PIXEL4 1
        set -gx DOOM_CELL_LUT 0
        set -gx DOOM_R17_PIXEL_DBRA 0
        set -gx DOOM_R19_FLAT_DBRA 0
        set -gx DOOM_R16_WEAPON_LIFT 2
        set defs $pixel '-DDOOM_R22_SOLID_TILES' '-DDOOM_R22_PAIR_LUT'
    end
    set defs $defs '-DDOOM_R22_SRAM_BLOCKLINKS' '-DDOOM_R26_FLOW' 
    if contains -- $v cell-play pixel4-play
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
    if contains -- $v cell-play cell-perf cell-profperf pixel4-play pixel4-perf
        set defs $defs '-DDOOM_R27_GROUP_SIDE'
    end
    if contains -- $v cell-play cell-perf cell-profperf pixel4-play pixel4-perf
        set defs $defs '-DDOOM_R27_GROUP_LINE'
    end
    if not contains -- $v cpu-base cpu-group cpu-fixed cpu-lowgroup cell-profperf
        set defs $defs '-DDOOM_R28_VIDEO_AUDIT'
    end
    # Identical visual assets for every variant: user's preferred adaptive Bayer 8x8.
    set -l dither bayer8
    # The proven R31 mixed 52 signed PCM SFX are unchanged, uncompressed.
    set -gx DOOM_R31_SFX_MODE mixed
    set -gx DOOM_R31_SFX_REPORT "$dest/sfx-$v.json"
    # The native art generator reads SOURCE bitmaps; this copy ensures it
    # cannot accidentally read the converted/stripped WAD of the last build.
    cp /tmp/r23-original.wad scripts/doom64.wad; or exit 1
    python3 scripts/lab/gen_r30_native.py --dither "$dither" --storage raw > "$dest/art-$v.json"; or exit 1
    # Doom game uses the episode-converted WAD. Original 240x160 bitmaps
    # are omitted by repack_wad in R30_NATIVE variants.
    cp /tmp/r23-converted.wad scripts/doom64.wad; or exit 1
    python3 scripts/lab/prepare_r25_music.py; or exit 1
    if set -q DOOM_R51_HW_WEAPON; and test "$DOOM_R51_HW_WEAPON" = 1
        if test "$v" != pixel4-play
            echo 'R51 hardware weapon requires Pair-V PLAY'; exit 2
        end
        if not set -q DOOM_R48_PAIR_V; or test "$DOOM_R48_PAIR_V" != 1
            echo 'R51 hardware weapon requires Pair-V'; exit 2
        end
        # Pixel art is converted from the same playable episode WAD.
        # No runtime decoding, sprite heap, extra frame buffer or DMA scratch.
        python3 scripts/lab/gen_r51_hw_weapon.py; or exit 1
    end
    if test "$DOOM_R29_XGM2" = 1
        set defs $defs '-DDOOM_R29_XGM2'
    end
    if test "$DOOM_R29_MULTI" = 1
        set defs $defs '-DDOOM_R29_MULTI'
    end
    if test "$DOOM_R30_NATIVE" = 1
        set defs $defs '-DDOOM_R30_NATIVE'
    end
    if test "$DOOM_R31_SFX_MODE" != silent
        set defs $defs '-DDOOM_R31_SFX'
    end
    set defs $defs '-DDOOM_R35_ART_RAW'
    if set -q DOOM_R35D_CHECKER; and test "$DOOM_R35D_CHECKER" = 1; and contains -- $v cell-play cell-perf cell-profperf
        set defs $defs '-DDOOM_R35D_CHECKER'
        set -gx DOOM_R35D_REPORT "$dest/dither-$v.json"
    else
        set -e DOOM_R35D_REPORT
    end
    if set -q DOOM_R37_BSP_PROFILE; and test "$DOOM_R37_BSP_PROFILE" = 1; and test "$v" = cell-play
        # Only live gameplay is instrumented. The timedemo remains clean.
        set defs $defs '-DDOOM_R37_BSP_PROFILE'
    end
    if set -q DOOM_R38_TIME_PROFILE; and test "$DOOM_R38_TIME_PROFILE" = 1; and contains -- $v cell-play cell-profperf
        # Independent of old DOOM_ROUTINE_PROFILE env, which forces TIMEDEMO.
        # DOOM_R7_PROFILE enables the already-tested nested stage boundaries.
        set defs $defs '-DDOOM_R38_TIME_PROFILE'
    end
    # R39c independent SRAM optimizations.  Exactly one experiment per ROM.
    if set -q DOOM_R39C_VARIANT
        switch "$DOOM_R39C_VARIANT"
            case mcache
                set defs $defs '-DDOOM_R39C_MOVEP_CACHE'
            case mmap
                set defs $defs '-DDOOM_R39C_MOVEP_MAP'
            case mall
                set defs $defs '-DDOOM_R39C_MOVEP_CACHE' '-DDOOM_R39C_MOVEP_MAP'
            case reuse
                set defs $defs '-DDOOM_R39C_REUSE_CACHE'
            case control
            case '*'
                echo "Unknown R39c experiment: $DOOM_R39C_VARIANT"
                exit 2
        end
    end
    if set -q DOOM_R39D_DITHER_TOGGLE; and test "$DOOM_R39D_DITHER_TOGGLE" = 1
        if contains -- $v cell-play cell-perf
            set defs $defs '-DDOOM_R39D_DITHER_TOGGLE'
        else
            echo 'R39d runtime dither toggle supports 8x8 cell variants only'
            exit 2
        end
    end
    if set -q DOOM_R39E_AUDIO_TOGGLES; and test "$DOOM_R39E_AUDIO_TOGGLES" = 1
        if contains -- $v cell-play cell-perf pixel4-play pixel4-perf
            set defs $defs '-DDOOM_R39E_AUDIO_TOGGLES'
        else
            echo 'R39e audio toggles support playable/timedemo renderers only'
            exit 2
        end
    end
    if set -q DOOM_R39F_DITHER3; and test "$DOOM_R39F_DITHER3" = 1
        if not contains -- $v cell-play cell-perf
            echo 'R39f tri-state dithering supports 8x8 cell variants only'
            exit 2
        end
        if not set -q DOOM_R39D_DITHER_TOGGLE; or test "$DOOM_R39D_DITHER_TOGGLE" != 1
            echo 'R39f requires DOOM_R39D_DITHER_TOGGLE=1'
            exit 2
        end
        if not set -q DOOM_R35D_CHECKER; or test "$DOOM_R35D_CHECKER" != 1
            echo 'R39f requires the original R35d checker tiles'
            exit 2
        end
        set defs $defs '-DDOOM_R39F_DITHER3'
    end
    if set -q DOOM_R42_WALL_ASM; and test "$DOOM_R42_WALL_ASM" = 1
        if not contains -- $v pixel4-perf pixel4-play
            echo 'R42 ASM wall kernel requires native pixel4'; exit 2
        end
        set defs $defs '-DDOOM_R42_WALL_ASM'
    end
    if set -q DOOM_R47_FLAT_HOIST; and test "$DOOM_R47_FLAT_HOIST" = 1
        if not contains -- $v pixel4-perf pixel4-play
            echo 'R47 flat hoist must use independent pixel4 path'; exit 2
        end
        if not set -q DOOM_R42_WALL_ASM; or test "$DOOM_R42_WALL_ASM" != 1
            echo 'R47 flat hoist comparison requires R45 ASM wall baseline'; exit 2
        end
        set defs $defs '-DDOOM_R47_FLAT_HOIST'
    end
    if set -q DOOM_R47_SPRITE_HOIST; and test "$DOOM_R47_SPRITE_HOIST" = 1
        if not contains -- $v pixel4-perf pixel4-play
            echo 'R47 sprite hoist requires independent pixel4 path'; exit 2
        end
        set defs $defs '-DDOOM_R47_SPRITE_HOIST'
    end
    if set -q DOOM_R48_P0_PROFILE; and test "$DOOM_R48_P0_PROFILE" = 1
        if test "$v" != pixel4-perf
            echo 'R48 P0 counters are only valid on pixel4-perf'; exit 2
        end
        if not set -q DOOM_R47_PLANE_PAIR; or test "$DOOM_R47_PLANE_PAIR" != 1
            echo 'R48 P0 requires R47 Plane-Pair-H'; exit 2
        end
        if not set -q DOOM_R47_FLAT_HOIST; or test "$DOOM_R47_FLAT_HOIST" != 1
            echo 'R48 P0 requires R47 Flat-Hoist'; exit 2
        end
        if not set -q DOOM_R47_SPRITE_HOIST; or test "$DOOM_R47_SPRITE_HOIST" != 1
            echo 'R48 P0 requires R47 Sprite-Hoist'; exit 2
        end
        set defs $defs '-DDOOM_R48_P0_PROFILE'
    end
    if set -q DOOM_R47_PLANE_PAIR; and test "$DOOM_R47_PLANE_PAIR" = 1
        if not contains -- $v pixel4-perf pixel4-play
            echo 'R47 plane-pair requires independent pixel4 path'; exit 2
        end
        set defs $defs '-DDOOM_R47_PLANE_PAIR'
    end
    if set -q DOOM_R48_PAIR_V; and test "$DOOM_R48_PAIR_V" = 1
        if not contains -- $v pixel4-perf pixel4-play
            echo 'R48 Pair-V requires pixel4'; exit 2
        end
        if not set -q DOOM_R47_PLANE_PAIR; or test "$DOOM_R47_PLANE_PAIR" != 1
            echo 'R48 Pair-V requires R47 Plane-Pair'; exit 2
        end
        set defs $defs '-DDOOM_R48_PAIR_V'
    end
    if set -q DOOM_R48_V_FAST; and test "$DOOM_R48_V_FAST" = 1
        if not set -q DOOM_R48_PAIR_V; or test "$DOOM_R48_PAIR_V" != 1
            echo 'R48 Pair-V fast kernels require Pair-V'; exit 2
        end
        set defs $defs '-DDOOM_R48_V_FAST'
    end
    if set -q DOOM_R48_V_DITHER50; and test "$DOOM_R48_V_DITHER50" = 1
        if not set -q DOOM_R48_PAIR_V; or test "$DOOM_R48_PAIR_V" != 1
            echo 'R48 50/50 prototype requires Pair-V'; exit 2
        end
        set defs $defs '-DDOOM_R48_V_DITHER50'
    end
    for ratio in DOOM_R48_V_DITHER75A DOOM_R48_V_DITHER75B
        if set -q $ratio; and test "$ratio" = 1
            if not set -q DOOM_R48_PAIR_V; or test "$DOOM_R48_PAIR_V" != 1
                echo "R48 $ratio requires Pair-V"; exit 2
            end
            set defs $defs "-D$ratio"
        end
    end
    if set -q DOOM_R49_COLORMIX; and test "$DOOM_R49_COLORMIX" = 1
        if not test "$DOOM_R48_PAIR_V" = 1; or not test "$DOOM_R48_V_FAST" = 1
            echo 'R49 ColorMix needs Pair-V Fast'; exit 2
        end
        set defs $defs '-DDOOM_R49_COLORMIX'
    end
    if set -q DOOM_R49_COMPLUT; and test "$DOOM_R49_COMPLUT" = 1
        if not test "$DOOM_R48_PAIR_V" = 1
            echo 'R49 composed LUT needs Pair-V'; exit 2
        end
        set defs $defs '-DDOOM_R49_COMPLUT'
    end
    if set -q DOOM_R49_RATIO
        switch "$DOOM_R49_RATIO"
            case none 50
            case 75a
                if not test "$DOOM_R49_COLORMIX" = 1
                    echo '75a needs ColorMix'; exit 2
                end
                set defs $defs '-DDOOM_R49_MIX_75A'
            case 75b
                if not test "$DOOM_R49_COLORMIX" = 1
                    echo '75b needs ColorMix'; exit 2
                end
                set defs $defs '-DDOOM_R49_MIX_75B'
            case '*'
                echo 'Unknown R49 ColorMix ratio'; exit 2
        end
    end
    if set -q DOOM_R52_AB; and test "$DOOM_R52_AB" = 1
        if not test "$DOOM_R48_PAIR_V" = 1; or not test "$DOOM_R48_V_FAST" = 1
            echo 'R52-AB requires Pair-V Fast'; exit 2
        end
        if test "$DOOM_R49_COLORMIX" = 1; or test "$DOOM_R49_COMPLUT" = 1
            echo 'R52-AB cannot combine with R49 ColorMix'; exit 2
        end
        set defs $defs '-DDOOM_R52_AB'
    end
    if set -q DOOM_R52_CPLUT; and test "$DOOM_R52_CPLUT" = 1
        if not set -q DOOM_R52_CLAUDIO; or test "$DOOM_R52_CLAUDIO" != 1
            echo 'R52 composed lookup requires Claudio generator'; exit 2
        end
        set defs $defs '-DDOOM_R52_CPLUT'
    end
    if set -q DOOM_R51_HW_WEAPON; and test "$DOOM_R51_HW_WEAPON" = 1
        set defs $defs '-DDOOM_R51_HW_WEAPON'
    end
    if set -q DOOM_R51_HW_HUD; and test "$DOOM_R51_HW_HUD" = 1
        if not set -q DOOM_R51_HW_WEAPON; or test "$DOOM_R51_HW_WEAPON" != 1
            echo 'R51 HUD mask requires hardware weapon'; exit 2
        end
        set defs $defs '-DDOOM_R51_HW_HUD'
    end
    if set -q DOOM_R51_HW_CONTINUOUS; and test "$DOOM_R51_HW_CONTINUOUS" = 1
        if not set -q DOOM_R51_HW_WEAPON; or test "$DOOM_R51_HW_WEAPON" != 1
            echo 'R51 pistol continuity requires hardware weapon'; exit 2
        end
        set defs $defs '-DDOOM_R51_HW_CONTINUOUS'
    end
    if set -q DOOM_R51_NO_PSPRITE; and test "$DOOM_R51_NO_PSPRITE" = 1
        if test "$v" != pixel4-perf
            echo 'R51 no-weapon ablation is PERF-only'; exit 2
        end
        if set -q DOOM_R51_HW_WEAPON; and test "$DOOM_R51_HW_WEAPON" = 1
            echo 'R51 no-weapon and hw-gun are mutually exclusive'; exit 2
        end
        set defs $defs '-DDOOM_R51_NO_PSPRITE'
    end
    if set -q DOOM_R50_PLAY_BENCH; and test "$DOOM_R50_PLAY_BENCH" = 1
        if test "$v" != pixel4-play
            echo 'R50 menu benchmark is pixel4 PLAY only'; exit 2
        end
        if not set -q DOOM_R48_PAIR_V; or test "$DOOM_R48_PAIR_V" != 1
            echo 'R50 PLAY benchmark requires Pair-V'; exit 2
        end
        set defs $defs '-DDOOM_R50_PLAY_BENCH'
    end
    if set -q DOOM_R50_MENU_FREEZE; and test "$DOOM_R50_MENU_FREEZE" = 1
        if test "$v" != pixel4-play
            echo 'R50 menu freeze is pixel4 PLAY only'; exit 2
        end
        set defs $defs '-DDOOM_R50_MENU_FREEZE'
    end
    if set -q DOOM_R50_STATIC_MENU; and test "$DOOM_R50_STATIC_MENU" = 1
        if test "$v" != pixel4-play
            echo 'R50 static menu fix is Pair-V PLAY only'; exit 2
        end
        set defs $defs '-DDOOM_R50_STATIC_MENU'
    end
    if set -q DOOM_R50_HARD_REINIT; and test "$DOOM_R50_HARD_REINIT" = 1
        if test "$v" != pixel4-play
            echo 'R50 soft reset hard reinit needs pixel4-play'; exit 2
        end
        set defs $defs '-DDOOM_R50_HARD_REINIT'
    end
    if set -q DOOM_R50_RESET_SRAM; and test "$DOOM_R50_RESET_SRAM" = 1
        if test "$v" != pixel4-play
            echo 'R50 reset SRAM experiment is PLAY only'; exit 2
        end
        set defs $defs '-DDOOM_R50_RESET_SRAM'
    end
    if set -q DOOM_R47_MUL_BSP; and test "$DOOM_R47_MUL_BSP" = 1
        if not contains -- $v cell-perf cell-play
            echo 'R47 BSP multiply experiment requires 8x8 cell backend'; exit 2
        end
        set defs $defs '-DDOOM_R47_MUL_BSP'
    end
    if set -q DOOM_R47_MUL_LOGIC; and test "$DOOM_R47_MUL_LOGIC" = 1
        if not contains -- $v cell-perf cell-play
            echo 'R47 logic multiply experiment requires 8x8 cell backend'; exit 2
        end
        set defs $defs '-DDOOM_R47_MUL_LOGIC'
    end
    if set -q DOOM_R47_STATE_HASH; and test "$DOOM_R47_STATE_HASH" = 1
        if test "$v" != cell-perf
            echo 'R47 state hash is a DEMO3 cell-perf oracle'; exit 2
        end
        set defs $defs '-DDOOM_R47_STATE_HASH'
    end
    if set -q DOOM_R43_GRAY_CRT; and test "$DOOM_R43_GRAY_CRT" = 1
        if not contains -- $v pixel4-perf pixel4-play
            echo 'R43 grayscale requires native pixel4'; exit 2
        end
        set defs $defs '-DDOOM_R43_GRAY_CRT'
    end
    if set -q DOOM_R46_M1; and test "$DOOM_R46_M1" = 1
        if not contains -- $v cell-perf cell-play
            echo 'R46 M1 requires primary R39f cell backend'
            exit 2
        end
        if not set -q DOOM_R39F_DITHER3; or test "$DOOM_R39F_DITHER3" != 1
            echo 'R46 M1 requires full R39f tri-dither'
            exit 2
        end
        set defs $defs '-DDOOM_R46_M1'
    end
    if set -q DOOM_R46_M1B; and test "$DOOM_R46_M1B" = 1
        if not set -q DOOM_R46_M1; or test "$DOOM_R46_M1" != 1
            echo 'R46 M1B requires the dual-linked M1A backend'
            exit 2
        end
        if not contains -- $v cell-perf cell-play
            echo 'R46 M1B prepares pixel4 VRAM alongside 8x8 cell'
            exit 2
        end
        set defs $defs '-DDOOM_R46_M1B'
    end
    if set -q DOOM_R46_M2A; and test "$DOOM_R46_M2A" = 1
        if not set -q DOOM_R46_M1B; or test "$DOOM_R46_M1B" != 1
            echo 'R46 M2A requires linked M1B secondary pixel4 kernels'
            exit 2
        end
        if not contains -- $v cell-perf cell-play
            echo 'R46 M2A must preserve primary 8x8 geometry until dispatch'
            exit 2
        end
        set defs $defs '-DDOOM_R46_M2A'
    end
    if set -q DOOM_R46_M2B; and test "$DOOM_R46_M2B" = 1
        if not set -q DOOM_R46_M2A; or test "$DOOM_R46_M2A" != 1
            echo 'R46 M2B needs linked M2A projection'
            exit 2
        end
        if not contains -- $v cell-perf cell-play
            echo 'R46 M2B keeps R39f 8x8 active until geometry dispatcher'
            exit 2
        end
        set defs $defs '-DDOOM_R46_M2B'
    end
    if set -q DOOM_R46_M2C; and test "$DOOM_R46_M2C" = 1
        if not set -q DOOM_R46_M2B; or test "$DOOM_R46_M2B" != 1
            echo 'R46 M2C requires native vertical M2B geometry'
            exit 2
        end
        if not contains -- $v cell-perf cell-play
            echo 'R46 M2C retains primary 8x8 until full geometry dispatcher'
            exit 2
        end
        set defs $defs '-DDOOM_R46_M2C'
    end
    if set -q DOOM_R46_M3B_DIAG; and test "$DOOM_R46_M3B_DIAG" = 1
        if not set -q DOOM_R46_M2C; or test "$DOOM_R46_M2C" != 1
            echo 'M3B video boot test requires R46 M2C'
            exit 2
        end
        if test "$v" != cell-perf
            echo 'M3B diagnostic only builds timedemo cell-perf'
            exit 2
        end
        set defs $defs '-DDOOM_R46_M3B_DIAG'
    end
    if set -q DOOM_R46_M3C_DIAG; and test "$DOOM_R46_M3C_DIAG" = 1
        if not set -q DOOM_R46_M2C; or test "$DOOM_R46_M2C" != 1
            echo 'M3C diagnostic requires the native 4x4 helper build'
            exit 2
        end
        if set -q DOOM_R46_M3B_DIAG; and test "$DOOM_R46_M3B_DIAG" = 1
            echo 'M3B and M3C video tests are mutually exclusive'
            exit 2
        end
        if test "$v" != cell-perf
            echo 'M3C boot diagnostic only builds cell-perf'
            exit 2
        end
        set defs $defs '-DDOOM_R46_M3C_DIAG'
        if set -q DOOM_R46_M3C_SAFE_BLANK; and test "$DOOM_R46_M3C_SAFE_BLANK" = 1
            set defs $defs '-DDOOM_R46_M3C_SAFE_BLANK'
        end
        if set -q DOOM_R46_M3C_STRESS; and test "$DOOM_R46_M3C_STRESS" = 1
            set defs $defs '-DDOOM_R46_M3C_STRESS'
        end
        if set -q DOOM_R46_M3C_FONT_RESTORE; and test "$DOOM_R46_M3C_FONT_RESTORE" = 1
            set defs $defs '-DDOOM_R46_M3C_FONT_RESTORE'
        end
        if set -q DOOM_R46_M3C_LATE_BUFFER; and test "$DOOM_R46_M3C_LATE_BUFFER" = 1
            if not set -q DOOM_R46_M3C_FONT_RESTORE; or test "$DOOM_R46_M3C_FONT_RESTORE" != 1
                echo 'R5 delayed R20 allocation requires the R3 explicit font restore'
                exit 2
            end
            set defs $defs '-DDOOM_R46_M3C_LATE_BUFFER'
        end
        if set -q DOOM_R46_M6A_LAYOUT; and test "$DOOM_R46_M6A_LAYOUT" = 1
            if not set -q DOOM_R46_M3C_LATE_BUFFER; or test "$DOOM_R46_M3C_LATE_BUFFER" != 1
                echo 'R6A oracle must use stable R5 deferred-video-heap diagnostic'
                exit 2
            end
            # Layout-only contract. Does NOT change tile indices/SGDK ABI/VDP.
            set defs $defs '-DDOOM_R46_M6A_LAYOUT'
        end
    end
    set -gx DOOM_R20_DEFINES (string join ' ' -- $defs)
    set -l id doom-md-r35d-$v
    if set -q DOOM_R37_BSP_PROFILE; and test "$DOOM_R37_BSP_PROFILE" = 1; and contains -- $v cell-play cell-perf
        set id doom-md-r37-$v
    end
    if set -q DOOM_R38_TIME_PROFILE; and test "$DOOM_R38_TIME_PROFILE" = 1; and contains -- $v cell-play cell-perf cell-profperf
        set id doom-md-r38-$v
    end
    if set -q DOOM_R39C_VARIANT
        set id doom-md-r39c-$DOOM_R39C_VARIANT-$v
    end
    if set -q DOOM_R39D_BUILD
        switch "$DOOM_R39D_BUILD"
            case control toggle
                set id doom-md-r39d-$DOOM_R39D_BUILD-$v
            case '*'
                echo "Unknown R39d build $DOOM_R39D_BUILD"
                exit 2
        end
    end
    if set -q DOOM_R39E_BUILD
        switch "$DOOM_R39E_BUILD"
            case control audio
                set id doom-md-r39e-$DOOM_R39E_BUILD-$v
            case '*'
                echo "Unknown R39e build $DOOM_R39E_BUILD"
                exit 2
        end
    end
    if set -q DOOM_R39F_BUILD
        switch "$DOOM_R39F_BUILD"
            case control dither3
                if test "$DOOM_R39F_BUILD" = dither3
                    if not set -q DOOM_R39F_DITHER3; or test "$DOOM_R39F_DITHER3" != 1
                        echo 'R39f dither3 build requires DOOM_R39F_DITHER3=1'
                        exit 2
                    end
                end
                set id doom-md-r39f-$DOOM_R39F_BUILD-$v
            case '*'
                echo "Unknown R39f build $DOOM_R39F_BUILD"
                exit 2
        end
    end
    if set -q DOOM_R40_STAGE1
        switch "$DOOM_R40_STAGE1"
            case base fast
                if string match -q 'pixel4-*' -- "$v"
                    set id doom-md-r40-$DOOM_R40_STAGE1-$v
                else if string match -q 'cell-*' -- "$v"
                    if test "$DOOM_R40_STAGE1" != fast
                        echo 'R40 stage1 cell renderer uses only fast (R39e) build'
                        exit 2
                    end
                    set id doom-md-r40-$v
                else
                    echo 'R40 stage1 only supports cell and pixel4 play/perf'
                    exit 2
                end
            case '*'
                echo "Unknown R40 Stage1 variant $DOOM_R40_STAGE1"
                exit 2
        end
    end
    if set -q DOOM_R40A_BUILD; and test "$DOOM_R40A_BUILD" = 1
        if contains -- $v pixel4-play pixel4-perf
            set id doom-md-r40a-$v
        else
            echo 'R40a fixes the pixel4 native picture overlay only'
            exit 2
        end
    end
    if set -q DOOM_R40B_BUILD; and test "$DOOM_R40B_BUILD" = 1
        if contains -- $v pixel4-play pixel4-perf
            set id doom-md-r40b-$v
        else
            echo 'R40b is a pixel4 title/intermission WINDOW change only'
            exit 2
        end
    end
    if set -q DOOM_R40C_M0; and test "$DOOM_R40C_M0" = 1
        if contains -- $v cell-play cell-perf pixel4-play pixel4-perf
            set id doom-md-r40c-$v
        else
            echo 'R40c M0 controls support only cell/pixel4 play/perf'
            exit 2
        end
    end
    if set -q DOOM_R45_VARIANT
        switch "$DOOM_R45_VARIANT"
            case cell
                if not contains -- $v cell-perf cell-play
                    echo 'R45 cell variant needs 8x8 renderer'; exit 2
                end
                if not set -q DOOM_R39F_DITHER3; or test "$DOOM_R39F_DITHER3" != 1
                    echo 'R45 cell requires R39f dither3'; exit 2
                end
                set id doom-md-r45-$v
            case asm gray
                if not contains -- $v pixel4-perf pixel4-play
                    echo 'R45 pixel4 variants require pixel4 renderer'; exit 2
                end
                if not set -q DOOM_R42_WALL_ASM; or test "$DOOM_R42_WALL_ASM" != 1
                    echo 'R45 pixel4 variants require R42 ASM'; exit 2
                end
                if test "$DOOM_R45_VARIANT" = gray
                    if not set -q DOOM_R43_GRAY_CRT; or test "$DOOM_R43_GRAY_CRT" != 1
                        echo 'R45 gray requires R43 gray palette'; exit 2
                    end
                end
                if test "$v" = pixel4-perf
                    set id doom-md-r45-$DOOM_R45_VARIANT-p4perf
                else
                    set id doom-md-r45-$DOOM_R45_VARIANT-p4play
                end
            case '*'
                echo 'Unknown R45 variant'; exit 2
        end
    end
    if set -q DOOM_R46_BUILD
        switch "$DOOM_R46_BUILD"
            case primary m1 m1b m2a m2b m2c
                if test "$DOOM_R46_BUILD" = m2c
                    if not set -q DOOM_R46_M2C; or test "$DOOM_R46_M2C" != 1
                        echo 'R46 m2c profile requires M2C feature flag'
                        exit 2
                    end
                end
                if test "$DOOM_R46_BUILD" = m2b
                    if not set -q DOOM_R46_M2B; or test "$DOOM_R46_M2B" != 1
                        echo 'R46 m2b profile requires M2B flag'
                        exit 2
                    end
                end
                if test "$DOOM_R46_BUILD" = m2a
                    if not set -q DOOM_R46_M2A; or test "$DOOM_R46_M2A" != 1
                        echo 'R46 m2a profile requires M2A feature flag'
                        exit 2
                    end
                end
                if test "$DOOM_R46_BUILD" = m1b
                    if not set -q DOOM_R46_M1B; or test "$DOOM_R46_M1B" != 1
                        echo 'R46 m1b ID requires M1B feature'
                        exit 2
                    end
                end
                if not contains -- $v cell-perf cell-play
                    echo 'R46 primary/M1 must be 8x8 cell'
                    exit 2
                end
                if test "$v" = cell-perf
                    set id doom-md-r46-$DOOM_R46_BUILD-perf
                else
                    set id doom-md-r46-$DOOM_R46_BUILD-play
                end
            case '*'
                echo 'Invalid R46 build profile'
                exit 2
        end
    end
    if set -q DOOM_R46_M3B_DIAG; and test "$DOOM_R46_M3B_DIAG" = 1
        set id doom-md-r46-m3b-video-perf
    end
    if set -q DOOM_R46_M3C_DIAG; and test "$DOOM_R46_M3C_DIAG" = 1
        if set -q DOOM_R46_M3C_SAFE_BLANK; and test "$DOOM_R46_M3C_SAFE_BLANK" = 1
            if set -q DOOM_R46_M3C_FONT_RESTORE; and test "$DOOM_R46_M3C_FONT_RESTORE" = 1
                if set -q DOOM_R46_M3C_LATE_BUFFER; and test "$DOOM_R46_M3C_LATE_BUFFER" = 1
                    if set -q DOOM_R46_M6A_LAYOUT; and test "$DOOM_R46_M6A_LAYOUT" = 1
                        set id doom-md-r46-r6a-audit-safe
                    else
                        set id doom-md-r46-r5-late-safe
                    end
                else
                    set id doom-md-r46-m3c-r3-safe-perf
                end
            else
                set id doom-md-r46-m3c-r2-safe-perf
            end
        else if set -q DOOM_R46_M3C_STRESS; and test "$DOOM_R46_M3C_STRESS" = 1
            if set -q DOOM_R46_M3C_FONT_RESTORE; and test "$DOOM_R46_M3C_FONT_RESTORE" = 1
                if set -q DOOM_R46_M3C_LATE_BUFFER; and test "$DOOM_R46_M3C_LATE_BUFFER" = 1
                    if set -q DOOM_R46_M6A_LAYOUT; and test "$DOOM_R46_M6A_LAYOUT" = 1
                        set id doom-md-r46-r6a-audit-stress
                    else
                        set id doom-md-r46-r5-late-stress
                    end
                else
                    set id doom-md-r46-m3c-r3-stress-perf
                end
            else
                set id doom-md-r46-m3c-r2-stress-perf
            end
        else
            set id doom-md-r46-m3c-video-perf
        end
    end
    if set -q DOOM_R47_FLAT_HOIST; and test "$DOOM_R47_FLAT_HOIST" = 1
        if test "$v" = pixel4-perf
            set id doom-md-r47a-flat-p4perf
        else
            set id doom-md-r47a-flat-p4play
        end
    end
    if set -q DOOM_R47_BUILD
        if string match -qr '[^a-z0-9-]' -- "$DOOM_R47_BUILD"
            echo 'Invalid R47 build id'; exit 2
        end
        set id doom-md-r47-$DOOM_R47_BUILD
    end
    if set -q DOOM_R48_BUILD
        if string match -qr '[^a-z0-9-]' -- "$DOOM_R48_BUILD"
            echo 'Invalid R48 build id'; exit 2
        end
        set id doom-md-r48-$DOOM_R48_BUILD
    end
    if set -q DOOM_R49_BUILD
        if string match -qr '[^a-z0-9-]' -- "$DOOM_R49_BUILD"
            echo 'Invalid R49 build id'; exit 2
        end
        set id doom-md-r49-$DOOM_R49_BUILD
    end
    if set -q DOOM_R50_BUILD
        if string match -qr '[^a-z0-9-]' -- "$DOOM_R50_BUILD"
            echo 'Invalid R50 build id'; exit 2
        end
        set id doom-md-r50-$DOOM_R50_BUILD
    end
    if set -q DOOM_R51_BUILD
        if string match -qr '[^a-z0-9-]' -- "$DOOM_R51_BUILD"
            echo 'Invalid R51 build id'; exit 2
        end
        set id doom-md-r51-$DOOM_R51_BUILD
    end
    if set -q DOOM_R52_BUILD
        if string match -qr '[^a-z0-9-]' -- "$DOOM_R52_BUILD"
            echo 'Invalid R52 build id'; exit 2
        end
        set id doom-md-r52-$DOOM_R52_BUILD
    end
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
    python3 scripts/lab/finish_r35_rom.py out/rom.bin "$dest/$id.bin"; or exit 1
    cp out/release/rom.out "$dest/$id.elf"; or exit 1
    cp out/.render_options "$dest/flags-$id.txt"; or exit 1
    # The ELF's raw loadable image is the real occupied ROM content, unlike
    # sizebnd's 128 KiB-rounded .bin. Compare actual linked footprint against our 4 MiB cap.
    set -l rawout "$dest/_payload-$v.tmp"
    "$HOME/mars/m68k-elf/bin/m68k-elf-objcopy" -O binary out/release/rom.out "$rawout"; or exit 1
    stat -c %s "$rawout" > "$dest/payload-$v.txt"; or exit 1
    rm -f "$rawout"
    set built $built $id
end
cp /tmp/r23-original.wad scripts/doom64.wad; or exit 1
if test (count $argv) -eq 0
    # Whole-batch local run: check all 4 ROMs after the loop.
    python3 scripts/lab/audit_r35.py "$dest" $variants; or exit 1
end
# CI invokes one variant per subprocess and performs this shared audit only
# AFTER all four builds are complete.
sha256sum $dest/*.bin > "$dest/SHA256SUMS"
echo "READY: R35 4MiB linear, Bayer8 raw artwork, 52 mixed PCM, XGM2 untouched, 8x8/4x4 play+perf"
