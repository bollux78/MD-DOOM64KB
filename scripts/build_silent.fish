#!/usr/bin/env fish
# Doom Mega Drive: silent build using an existing SGDK toolchain.
# Never edits the shared toolchain.
set -l root (pwd)
if set -q DOOM_MD_ROOT
    set root $DOOM_MD_ROOT
end
set -l gdk $HOME/mars/m68k-elf
if set -q DOOM_MD_GDK
    set gdk $DOOM_MD_GDK
end
set -l gcc $gdk/bin/m68k-elf-gcc
if not test -f $root/Makefile; or not test -f $gdk/makefile.gen; or not test -f $gdk/lib/libmd.a; or not test -x $gcc
    echo 'Missing Doom source or SGDK / m68k-elf GCC:' $root $gdk
    exit 1
end
cd $root; or exit 1
python3 -c 'import pathlib,struct
root=pathlib.Path("res")
root.mkdir(parents=True,exist_ok=True)
data=bytes([0x52,0x28,0x00,0x62,0x66])
header=bytearray(0x40)
header[:4]=b"Vgm "
struct.pack_into("<I",header,4,len(header)+len(data)-4)
struct.pack_into("<I",header,8,0x00000150)
struct.pack_into("<I",header,0x2c,7670454)
struct.pack_into("<I",header,0x18,735)
struct.pack_into("<I",header,0x34,0x0c)
for name in ("silent.vgm","e1m1.vgm"):
    path=root/name
    if not path.exists(): path.write_bytes(header+data)
'; or exit 1
set -lx GDK $gdk
set -lx PATH $gdk/bin $PATH
set -lx PREFIX m68k-elf-
if not test -f scripts/doom64.wad
    python3 scripts/wad_from_header.py; or exit 1
end
python3 scripts/repack_wad.py; or exit 1
python3 scripts/genpal.py; or exit 1
if set -q DOOM_CELL_LUT; and test "$DOOM_CELL_LUT" = 1
    python3 scripts/gen_colormap_cells.py; or exit 1
end
python3 scripts/gen_sfx.py --silent; or exit 1
# Use SGDK boot files; disable the duplicate upstream boot and ROM header
# only inside the Doom working tree.
for f in src/boot/sega.s src/boot/rom_head.c
    if test -f $f
        mv $f $f.disabled
    end
end
set -l render_flags '-DFLAT_SPAN -DFLAT_NUKAGE1_COLOR=118 -DVIEWWINDOWWIDTH=38 -DVIEWWINDOWHEIGHT=28 -DMAPWIDTH=38 -DLOW_MEMORY -DSFX_SILENT'
if set -q DOOM_TIMEDEMO; and test "$DOOM_TIMEDEMO" = 1
    set render_flags "$render_flags -DTIMEDEMO"
end
if set -q DOOM_ROUTINE_PROFILE; and test "$DOOM_ROUTINE_PROFILE" = 1
    set render_flags "$render_flags -DTIMEDEMO -DDOOM_ROUTINE_PROFILE"
end
if set -q DOOM_PROFILE; and test "$DOOM_PROFILE" = 1
    set render_flags "$render_flags -DTIMEDEMO -DDOOM_PROFILE"
end
if not set -q DOOM_NO_VSYNC; or test "$DOOM_NO_VSYNC" != 0
    set render_flags "$render_flags -DDOOM_NO_VSYNC"
end
# Experimental renderer switches are local to this ROM, never global SGDK.
if set -q DOOM_FAST_DIVU; and test "$DOOM_FAST_DIVU" = 1
    set render_flags "$render_flags -DDOOM_FAST_DIVU"
end
if set -q DOOM_UNROLL_COLUMNS; and test "$DOOM_UNROLL_COLUMNS" = 1
    set render_flags "$render_flags -DDOOM_UNROLL_COLUMNS"
end
if set -q DOOM_CELL_LUT; and test "$DOOM_CELL_LUT" = 1
    set render_flags "$render_flags -DDOOM_CELL_LUT"
end
if set -q DOOM_FOLDED_TANGENT; and test "$DOOM_FOLDED_TANGENT" = 1
    set render_flags "$render_flags -DDOOM_FOLDED_TANGENT"
end
if set -q DOOM_MASKED_DIVU; and test "$DOOM_MASKED_DIVU" = 1
    set render_flags "$render_flags -DDOOM_MASKED_DIVU"
end
if set -q DOOM_CACHE8; and test "$DOOM_CACHE8" = 1
    set render_flags "$render_flags -DDOOM_CACHE8"
end
# Round 4 cache slot sizes and separate cache-stat diagnostics.
if set -q DOOM_CACHE_SLOTS
    switch "$DOOM_CACHE_SLOTS"
        case 8 16 32 64
            set render_flags "$render_flags -DDOOM_CACHE_SLOTS=$DOOM_CACHE_SLOTS"
        case '*'
            echo "Invalid DOOM_CACHE_SLOTS: $DOOM_CACHE_SLOTS (expected 8, 16, 32 or 64)"
            exit 1
    end
end
if set -q DOOM_CACHE_STATS; and test "$DOOM_CACHE_STATS" = 1
    if not set -q DOOM_CACHE_SLOTS
        echo 'DOOM_CACHE_STATS requires DOOM_CACHE_SLOTS'
        exit 1
    end
    set render_flags "$render_flags -DDOOM_CACHE_STATS"
end
# Generate matching ROM header and on-screen timedemo title per build.
# SGDK's makefile.gen compiles src/rom_header.c into out/rom_header.bin.
# No changes to shared SGDK files or boot code are required.
set -l stamp_options "$render_flags"
if set -q DOOM_BUILD_ID
    python3 scripts/set_rom_identity.py --id "$DOOM_BUILD_ID"; or exit 1
    set render_flags "$render_flags -DDOOM_BUILD_VARIANT"
    set stamp_options "$render_flags $DOOM_BUILD_ID"
end
set -l stamp out/.render_options
if test -f $stamp; and test (cat $stamp) != "$stamp_options"
    rm -rf out
end
mkdir -p out
printf '%s' "$stamp_options" > $stamp
rm -f out/rom.bin
set -l libgcc ($gcc -m68000 -print-libgcc-file-name)
if test $status -ne 0; or not test -f "$libgcc"
    echo 'Could not locate cross compiler libgcc.'
    exit 1
end
make GDK=$gdk PREFIX=m68k-elf- JAVA=java \
    EXTRA_FLAGS="-Isrc -Icompat -std=gnu11 $render_flags" \
    LIBGCC="$libgcc -lgcc" $argv
set -l rc $status
if test $rc -eq 0; and test -f out/rom.bin
    echo 'ROM created:' $root/out/rom.bin
else
    echo 'Build failed or ROM missing. Check output above.'
    if test $rc -eq 0
        set rc 1
    end
end
exit $rc
