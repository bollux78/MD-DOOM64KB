#!/usr/bin/env fish
set -l gdk /home/dan/mars/m68k-elf
if set -q GDK[1]
    set gdk $GDK
end
set -lx PATH $gdk/bin $PATH
mkdir -p build
or exit 1
m68k-elf-as -m68000 subcpu/boot.s -o build/subcpu.o
or exit 1
m68k-elf-gcc -m68000 -O2 -ffreestanding -fomit-frame-pointer -c subcpu/render.c -o build/subrender.o
or exit 1
m68k-elf-ld -Ttext=0 --entry=subcpu_vectors -o build/subcpu.elf build/subcpu.o build/subrender.o (m68k-elf-gcc -m68000 -print-libgcc-file-name)
or exit 1
m68k-elf-objcopy -O binary build/subcpu.elf build/subcpu.bin
or exit 1
python3 tools/make_sub_header.py build/subcpu.bin src/sub_program.h
or exit 1
make GDK=$gdk PREFIX=m68k-elf- -j1
or exit 1
set -l rom out/rom.bin
if test -f out/release/rom.bin
    set rom out/release/rom.bin
end
python3 tools/mark_mode1.py $rom build/doom-scd-visual-3d.bin
