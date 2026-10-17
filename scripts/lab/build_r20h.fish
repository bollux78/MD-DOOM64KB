#!/usr/bin/env fish
# R20h: complete 2^4 render/cache combinations on V3 + ROM color; 40 ROMs.
# Every ROM preserves S2 + DBRA + P2 + M1 + R2 and natural inlining.
# R3/R4/R4b/P3/S5/dynamic sprites/V2 stay disabled; no engine code changes.
# Usage: fish scripts/lab/build_r20h.fish
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r20h
mkdir -p "$dest"; or exit 1

function r20_flags_for --argument-names name
    python3 -c 'import json,sys; d=json.load(open("scripts/lab/r20h_matrix.json")); print(" ".join("-DDOOM_R20_"+f for f in d[sys.argv[1]]))' "$name"
end
set -l variants $argv
if test (count $variants) -eq 0
    set variants (python3 -c 'import json; print("\n".join(json.load(open("scripts/lab/r20h_matrix.json"))))')
end

python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r15_wallmul.py; or exit 1
python3 scripts/lab/test_r16_crt_hud.py; or exit 1
python3 scripts/lab/test_r17_pixel_loop.py; or exit 1
python3 scripts/lab/gen_r12_recip_lut.py --max-scale 65535; or exit 1

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

# Hardware-validated R2 base throughout. R4 stays disabled.
set -l common '-DDOOM_R20_SIGHT_ITERATIVE' '-DDOOM_R20_PIXEL_ADDX' '-DDOOM_R20_TAN_MULS' '-DDOOM_R20_CELLMAP_MEMO' '-DDOOM_R20_HUD_LAZY' '-DDOOM_R20_FPS_LAZY' '-DDOOM_R20_SCALE_MATH' '-DDOOM_R20_BSP_ITERATIVE'
set -l built
for v in $variants
    set -l defs $common
    for part in (string split '+' -- $v)
        set -l f (r20_flags_for $part)
        or begin
            echo "ERROR: unknown variant part '$part' in '$v'"
            exit 1
        end
        test -n "$f"; and set defs $defs $f
    end
    set -gx DOOM_R19_FLAT_DBRA 1
    set -gx DOOM_R20_DEFINES (string join ' ' -- $defs)
    set -l id doom-md-r20h-(string replace -a '+' '-' -- $v)
    set -gx DOOM_BUILD_ID $id
    if set -q DOOM_R20H_REUSE; and test -f "$dest/.reuse-verified"; and test -s "$dest/$id.bin"
        echo "REUSE VERIFIED: $id"
        set built $built $id
        continue
    end
    echo "BUILD: $id  [$DOOM_R20_DEFINES]"
    rm -rf out
    rm -f res/music.rs res/music.d
    fish scripts/build_silent.fish > "$dest/build-$id.log" 2>&1
    or begin
        echo "ERROR: compilation failed for $id"
        tail -n 80 "$dest/build-$id.log"
        exit 1
    end
    test -s out/rom.bin; or exit 1
    python3 -c 'import pathlib,struct,sys
p=pathlib.Path("out/rom.bin"); b=bytearray(p.read_bytes()); name=sys.argv[1]
assert 0x200 <= len(b) <= 0x400000, len(b)
assert b[0x120:0x150].decode("ascii").strip()==name
if len(b)>0x200000:
    struct.pack_into(">I",b,0x1a4,len(b)-1); p.write_bytes(b)
assert struct.unpack_from(">I",b,0x1a4)[0] >= len(b)-1
print("VERIFIED",name,len(b),"bytes")' "$id"; or exit 1
    cp out/rom.bin "$dest/$id.bin"; or exit 1
    cp out/.render_options "$dest/flags-$id.txt"; or exit 1
    test -s out/release/rom.out; or exit 1
    cp out/release/rom.out "$dest/$id.elf"; or exit 1
    set built $built $id
end

# S4 audit: compiler flags differ only by DOOM_R20_* defines, and the hot
# symbols' sizes show whether a block changed code outside its own function.
python3 scripts/lab/r20h_flags.py "$dest"; or exit 1
python3 scripts/lab/r20_layout_audit.py "$dest" $built; or exit 1
sha256sum $dest/*.bin > "$dest/SHA256SUMS"
echo "READY: $dest ("(count $built)" ROMs). Compare FPS only against doom-md-r20h-control. diag has overhead; control uses R20f-all (184.90 s BlastEm), still pending hardware validation."
