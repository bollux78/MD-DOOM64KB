#!/usr/bin/env fish
# Build a standalone, 5 MiB SSF2/SRAM hardware probe for the EverDrive-MD V2.
# It is deliberately NOT the Doom image: ROM banking is tested without
# introducing changes to the working renderer, music, or map code.
set -l root (realpath (dirname (status filename))/../..)
set -l gdk "$HOME/mars/m68k-elf"
if set -q DOOM_MD_GDK
    set gdk "$DOOM_MD_GDK"
end
set -l compiler "$gdk/bin/m68k-elf-gcc"
test -x "$compiler"; or begin
    echo "Missing compiler $compiler"
    exit 1
end
set -l output "$root/dist/r35"
set -l work "$root/out/r35-ssf-standalone"
mkdir -p "$work/src" "$output"; or exit 1
cp "$root/tools/r35-ssf-probe/main.c" "$work/src/main.c"; or exit 1
printf 'GDK ?= %s\nEXTRA_FLAGS ?= -std=gnu11\ninclude $(GDK)/makefile.gen\n' "$gdk" > "$work/Makefile"; or exit 1

set -lx PATH "$gdk/bin" $PATH
set -l libgcc ("$compiler" -m68000 -print-libgcc-file-name)
cd "$work"; or exit 1
make GDK="$gdk" PREFIX=m68k-elf- JAVA=java EXTRA_FLAGS="-std=gnu11" LIBGCC="$libgcc -lgcc"; or exit 1
test -s out/rom.bin; or begin
    echo 'SGDK did not generate the probe ROM'
    exit 1
end
python3 "$root/tools/r35-ssf-probe/patch_rom.py" out/rom.bin "$output/doom-md-r35-ssf-probe.bin"; or exit 1
sha256sum "$output/doom-md-r35-ssf-probe.bin" > "$output/SHA256SUMS"
echo "READY: $output/doom-md-r35-ssf-probe.bin"
