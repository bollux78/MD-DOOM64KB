#!/usr/bin/env fish
# R19 timedemo A/B: same R18 geometry, HUD, music and code; only flat DBRA differs.
# Both ROMs run DEMO3 automatically and show measured FPS at completion.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r19-flat-dbra-timedemo
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r15_wallmul.py; or exit 1
python3 scripts/lab/test_r16_crt_hud.py; or exit 1
python3 scripts/lab/test_r17_pixel_loop.py; or exit 1
python3 scripts/lab/test_r19_flat_dbra.py; or exit 1
python3 scripts/lab/gen_r12_recip_lut.py --max-scale 65535; or exit 1

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



# R17 DBRA validated on original Mega Drive; 10.55 FPS in BlastEm at divider 7.
set -gx DOOM_R15_TANMUL 0
set -gx DOOM_R15_SETUPMUL 1

set -gx DOOM_R16_HUD_UP2 1
set -gx DOOM_R16_WEAPON_LIFT 1

# Music must be an external real VGM, never a generated silent placeholder.
# Keep the source outside the Actions checkout so checkout clean cannot delete it.
set -l music "$HOME/Projetos/doom-assets/e1m1.vgm"
if set -q DOOM_R19_BGM_VGM
    set music "$DOOM_R19_BGM_VGM"
end
if not test -s "$music"
    echo "ERROR: E1M1 VGM not found: $music"
    echo 'Put it at ~/Projetos/doom-assets/e1m1.vgm or set DOOM_R19_BGM_VGM.'
    exit 2
end
python3 scripts/lab/check_r18_vgm.py "$music"; or exit 1
set -l source_path (realpath "$music"); or exit 1
set -l target_path "$root/res/e1m1.vgm"
mkdir -p "$root/res"; or exit 1
if test "$source_path" != "$target_path"
    cp -- "$source_path" "$target_path"; or exit 1
end
cmp -s -- "$source_path" "$target_path"; or exit 1

# Rescomp must always convert the NEW VGM, even if compiler flags are identical.
# The existing build_silent.fish will retain a real res/e1m1.vgm (it creates
# only missing placeholders). SFX remain silent until a real doom1.wad is added.
rm -rf out
rm -f res/music.rs res/music.d

set -gx DOOM_R16_HUD_UP2 1
set -gx DOOM_R16_WEAPON_LIFT 1
set -gx DOOM_R17_PIXEL_DBRA 1
set -gx DOOM_R17_FRAC_MULU 0
set -gx DOOM_R19_FLAT_DBRA 0
# Build IDs and only R19_FLAT_DBRA switch vary in the loop below.


for variant in control flat-dbra
    set -gx DOOM_R19_FLAT_DBRA 0
    switch $variant
        case control
            set -gx DOOM_BUILD_ID doom-md-r19-timedemo-control
        case flat-dbra
            set -gx DOOM_R19_FLAT_DBRA 1
            set -gx DOOM_BUILD_ID doom-md-r19-timedemo-flat-dbra
    end

    echo "BUILD: $DOOM_BUILD_ID (DEMO3 TIMEDEMO, E1M1 XGM music)"
    # Rebuild all objects and re-convert the identical VGM for both variants.
    rm -rf out
    rm -f res/music.rs res/music.d
    set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
    fish scripts/build_silent.fish > "$logfile" 2>&1
    if test $status -ne 0
        echo "ERROR: compilation failed for $DOOM_BUILD_ID"
        tail -n 130 "$logfile"
        exit 1
    end
    test -s out/rom.bin; or exit 1
    test -s out/.render_options; or exit 1
    set -l flags (cat out/.render_options)
    for required in '-DVIEWWINDOWWIDTH=38' '-DVIEWWINDOWHEIGHT=22' '-DDOOM_R16_HUD_UP2' '-DDOOM_R16_WEAPON_LIFT=1' '-DDOOM_R17_PIXEL_DBRA' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_HUD_DMA_STATUS_ONLY' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_CELL_LUT' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DDOOM_R10_DIST_DIVU' '-DDOOM_R11_TOPBAR_CLIP' '-DDOOM_R11_LEFTCOL_CLIP' '-DDOOM_R12_RECIP_LUT' '-DDOOM_R15_SETUPMUL=1' '-DDOOM_NO_VSYNC' '-DSFX_SILENT' '-DTIMEDEMO'
        string match -q -- "*$required*" "$flags"; or begin
            echo "ERROR: missing compiler flag $required for $DOOM_BUILD_ID"
            exit 1
        end
    end
    for forbidden in '-DPLAYTEST' '-DSFXDEBUG' '-DDOOM_PROFILE' '-DDOOM_ROUTINE_PROFILE' '-DDOOM_R17_FRAC_MULU' '-DDOOM_R15_TANMUL' '-DDOOM_R13_MUL_DECOMP' '-DDOOM_R14_CLIPSCAN' '-DDOOM_R14_BBOXSCAN'
        if string match -q -- "*$forbidden*" "$flags"
            echo "ERROR: unwanted compiler flag $forbidden"
            exit 1
        end
    end
    if test "$DOOM_R19_FLAT_DBRA" = 1
        string match -q -- '*-DDOOM_R19_FLAT_DBRA*' "$flags"; or begin
            echo 'ERROR: optimized ROM missing flat DBRA'
            exit 1
        end
    else if string match -q -- '*-DDOOM_R19_FLAT_DBRA*' "$flags"
        echo 'ERROR: control ROM unexpectedly enabled flat DBRA'
        exit 1
    end
    python3 -c 'import pathlib,struct,sys
p=pathlib.Path("out/rom.bin")
b=bytearray(p.read_bytes())
name=sys.argv[1]
assert 0x200 <= len(b) <= 0x400000, f"ROM size unsupported: {len(b)}"
assert b[0x120:0x150].decode("ascii").strip()==name
assert b[0x150:0x180].decode("ascii").strip()==name
if len(b)>0x200000:
    struct.pack_into(">I",b,0x1a4,len(b)-1)
    p.write_bytes(b)
assert struct.unpack_from(">I",b,0x1a4)[0] >= len(b)-1
print("VERIFIED timedemo",name,len(b),"bytes; ROM end",hex(struct.unpack_from(">I",b,0x1a4)[0]))
' "$DOOM_BUILD_ID"; or exit 1
    cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
    cp out/.render_options "$dest/flags-$DOOM_BUILD_ID.txt"; or exit 1
    if test -s out/release/rom.out
        cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
    end
end

# Ensure the compiler-option delta is precisely the one requested.
python3 - "$dest" <<'PY'
from pathlib import Path
import sys
d = Path(sys.argv[1])
a = (d / "flags-doom-md-r19-timedemo-control.txt").read_text().split()
b = (d / "flags-doom-md-r19-timedemo-flat-dbra.txt").read_text().split()
def strip_ident(flags):
    return sorted(x for x in flags if x != "-DDOOM_R19_FLAT_DBRA" and
                  not x.startswith("-DDOOM_BUILD_VARIANT"))
assert "-DDOOM_R19_FLAT_DBRA" not in a
assert "-DDOOM_R19_FLAT_DBRA" in b
assert strip_ident(a) == strip_ident(b), (
    "unexpected compiler flag differences",
    sorted(set(a) - set(b)), sorted(set(b) - set(a)))
print("PASS: control and optimized timedemo compiler flags differ only by flat DBRA")
PY
or exit 1

sha256sum res/e1m1.vgm > "$dest/e1m1-source-sha256.txt"; or exit 1
printf '%s\n' \
    'R19 DEMO3 timedemo A/B: same geometry, same music, same R17 textured DBRA.' \
    'CONTROL: R19_FLAT_DBRA disabled (R18 rendering baseline).' \
    'OPTIMIZED: R19_FLAT_DBRA enabled (68000 DBRA for flat-color columns).' \
    'Run both on BlastEm NTSC 60Hz, 68000 divider 7, same settings.' \
    'Wait for DEMO3 to finish and photograph the result screens.' \
    'Compare average FPS, minimum/maximum 1s FPS, presented frames, and elapsed time.' \
    'A/B compiler options are validated to differ only in the flat DBRA flag.' \
    'The R18 playable and R19 playable branches are untouched.' \
    > "$dest/README.txt"
echo "READY: $dest (two DEMO3 timedemo ROMs)"
