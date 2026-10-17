#!/usr/bin/env fish
# R22: first independent packed76x44/4x4 renderer; five ROMs.
# Base of EVERY ROM = R20h common flags + vc-all (V3, ROM color, R5, cache
# direct, R6, M2), natural inlining. Each variant adds DOOM_R21_* blocks (and,
# for the stability probes, the old R20 S5/V2 flags) from r21_matrix.json.
# Compare FPS only against doom-md-r21-control; hash/diag/cnt/prof ROMs carry
# instrumentation overhead and answer other questions (see docs/review-r21).
# Usage: fish scripts/lab/build_r21.fish [variant ...]
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r22b
mkdir -p "$dest"; or exit 1

set -l variants control p4-fixed play-fixed solid diag-solid play-solid solid-lut play-lut pattern-lut
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
set -l built
for v in $variants
    set -gx DOOM_R22_PIXEL4 0
    set -gx DOOM_TIMEDEMO 1
    set -gx DOOM_CELL_LUT 1
    set -gx DOOM_R17_PIXEL_DBRA 1
    set -gx DOOM_R19_FLAT_DBRA 1
    set -gx DOOM_R16_WEAPON_LIFT 1
    set -l defs $control
    if test "$v" != control
        set -gx DOOM_R22_PIXEL4 1
        set -gx DOOM_CELL_LUT 0
        set -gx DOOM_R17_PIXEL_DBRA 0
        set -gx DOOM_R19_FLAT_DBRA 0
        set -gx DOOM_R16_WEAPON_LIFT 2
        set defs $pixel
    end
    if contains -- $v solid diag-solid play-solid solid-lut play-lut pattern-lut
        set defs $defs '-DDOOM_R22_SOLID_TILES'
    end
    if contains -- $v solid-lut play-lut pattern-lut
        set defs $defs '-DDOOM_R22_PAIR_LUT'
    end
    if test "$v" = diag-solid
        set defs $defs '-DDOOM_R20_STACKGUARD' '-DDOOM_R21_STACK_PLAY'
    end
    if contains -- $v play-fixed play-solid play-lut pattern-lut
        set -gx DOOM_TIMEDEMO 0
    end
    if test "$v" = pattern-lut
        set defs $defs '-DDOOM_R22_PATTERN'
    end
    set -gx DOOM_R20_DEFINES (string join ' ' -- $defs)
    set -l id doom-md-r22b-$v
    set -gx DOOM_BUILD_ID $id
    echo "BUILD: $id  [$DOOM_R20_DEFINES]"
    rm -rf out
    rm -f res/music.rs res/music.d
    fish scripts/build_silent.fish > "$dest/build-$id.log" 2>&1
    or begin
        tail -n 100 "$dest/build-$id.log"
        exit 1
    end
    cp out/rom.bin "$dest/$id.bin"; or exit 1
    cp out/release/rom.out "$dest/$id.elf"; or exit 1
    cp out/.render_options "$dest/flags-$id.txt"; or exit 1
    set built $built $id
end
python3 scripts/lab/audit_r22.py "$dest"; or exit 1
sha256sum $dest/*.bin > "$dest/SHA256SUMS"
echo "READY: R22b nine-ROM 4x4 lab, game/hardware tests pending"
