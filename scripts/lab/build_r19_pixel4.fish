#!/usr/bin/env fish
# R19: experimental 4x4 pixel renderer at 80x44, with E1M1 music.
# Preserve R18 branch; this R19 ROM is NOT yet hardware-validated.
set -l root (realpath (dirname (status filename))/../..)
cd "$root"; or exit 1
set -l dest dist/r19-pixel4
mkdir -p "$dest"; or exit 1
python3 scripts/lab/test_r12_recip_lut.py; or exit 1
python3 scripts/lab/test_r15_wallmul.py; or exit 1
python3 scripts/lab/test_r19_pixel4.py; or exit 1
python3 scripts/lab/gen_r12_recip_lut.py --max-scale 65535; or exit 1

set -gx DOOM_TIMEDEMO 0
set -gx DOOM_NO_VSYNC 1
set -gx DOOM_FAST_DIVU 1
set -gx DOOM_CELL_LUT 0
set -gx DOOM_CACHE_SLOTS 16
set -gx DOOM_CACHE_STATS 0
set -gx DOOM_CLASSIC_TEXT_HUD 1
set -gx DOOM_HUD_DMA24 0
set -gx DOOM_HUD_DMA24_NOHUDWRITE 0
set -gx DOOM_HUD_DMA_STATUS_ONLY 0
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
set -gx DOOM_R11_TOPBAR_CLIP 0
set -gx DOOM_R11_TOPBAR_DMA 0
set -gx DOOM_R11_LEFTCOL_CLIP 0
set -e DOOM_ZONE_KIB



# R19: 80x44 logical pixels, 4x4 enlargement in H40. Baseline R18 remains unchanged.
set -gx DOOM_R15_TANMUL 0
set -gx DOOM_R15_SETUPMUL 1

set -gx DOOM_R16_HUD_UP2 1
set -gx DOOM_R16_WEAPON_LIFT 2

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
set -gx DOOM_R16_WEAPON_LIFT 2
set -gx DOOM_R17_PIXEL_DBRA 0
set -gx DOOM_R19_PIXEL4 1
set -gx DOOM_R17_FRAC_MULU 0
set -gx DOOM_BUILD_ID doom-md-r19-pixel4-e1m1

echo "BUILD: $DOOM_BUILD_ID (NO TIMEDEMO, E1M1 XGM music)"
set -l logfile "$dest/build-$DOOM_BUILD_ID.log"
fish scripts/build_silent.fish > "$logfile" 2>&1
if test $status -ne 0
    echo "ERROR: R19 compilation or VGM -> XGM conversion failed"
    tail -n 120 "$logfile"
    exit 1
end
test -s out/rom.bin; or exit 1
test -s out/.render_options; or exit 1
set -l flags (cat out/.render_options)
for required in '-DVIEWWINDOWWIDTH=80' '-DVIEWWINDOWHEIGHT=44' '-DMAPWIDTH=80' '-DDOOM_R19_PIXEL4' '-DDOOM_R16_HUD_UP2' '-DDOOM_R16_WEAPON_LIFT=2' '-DDOOM_CLASSIC_TEXT_HUD' '-DDOOM_CACHE_SLOTS=16' '-DDOOM_FAST_DIVU' '-DDOOM_R9_SLOPE_DIVU' '-DDOOM_R9_STEP_DIVS' '-DDOOM_R10_DIST_DIVU' '-DDOOM_R12_RECIP_LUT' '-DDOOM_R15_SETUPMUL=1' '-DDOOM_NO_VSYNC' '-DSFX_SILENT'
    string match -q -- "*$required*" "$flags"; or begin
        echo "ERROR: missing R19 compiler flag $required"
        exit 1
    end
end
for forbidden in '-DTIMEDEMO' '-DPLAYTEST' '-DDOOM_R17_PIXEL_DBRA' '-DDOOM_CELL_LUT' '-DDOOM_R11_TOPBAR_CLIP' '-DDOOM_R11_LEFTCOL_CLIP' '-DDOOM_HUD_DMA_STATUS_ONLY'
    if string match -q -- "*$forbidden*" "$flags"
        echo "ERROR: unwanted R19 compiler flag $forbidden"
        exit 1
    end
end
# Fix Genesis ROM-end metadata only if adding music grows the ROM past 2 MiB.
# The SGDK header generator defaults to 0x1fffff; larger music must not
# advertise a truncated ROM. The checksum excludes the header itself.
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
print("VERIFIED playable",name,len(b),"bytes; ROM end",hex(struct.unpack_from(">I",b,0x1a4)[0]))
' "$DOOM_BUILD_ID"; or exit 1
cp out/rom.bin "$dest/$DOOM_BUILD_ID.bin"; or exit 1
cp out/.render_options "$dest/flags-$DOOM_BUILD_ID.txt"; or exit 1
sha256sum res/e1m1.vgm > "$dest/e1m1-source-sha256.txt"; or exit 1
if test -s out/release/rom.out
    cp out/release/rom.out "$dest/$DOOM_BUILD_ID.elf"; or exit 1
end
printf '%s\n' \
    'R19 PIXEL4: experimental, not performance-validated; no timedemo, no PLAYTEST.' \
    'R19 EXPERIMENTAL: 80x44 logical pixels, 4x4 expanded to 320x176 in H40.' \
    'E1M1 external VGM converted by SGDK rescomp to XGM and embedded in ROM.' \
    'SFX_SILENT: no PCM sound effects; E1M1 XGM soundtrack is retained.' \
    'H40 40x22 unique patterns, 4 colors per tile, palette selected per tile.' \
    'Test on BlastEm first: boot, menus, walls, sprites, HUD, palette, frame rate.' \
    > "$dest/README.txt"
echo "READY: $dest/$DOOM_BUILD_ID.bin"
