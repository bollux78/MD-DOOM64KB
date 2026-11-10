#!/bin/bash
# usage: lbuild.sh OUTDIR [env...]   -> stage + build, prints rom path
set -e
out=$1; shift
rm -rf "$out"
env "$@" python3 /home/claude/md-doom64kb/experiments/DOOM_Manifold_E1M1/m01/stage_rom.py --source /home/claude/manifold-up --wad /home/claude/wad/d.wad --out "$out" > "$out.stage.log" 2>&1 || { tail -5 "$out.stage.log"; exit 1; }
ln -sf math3d.h "$out/src/math3D.h"
t=/home/claude/mars/m68k-elf/bin/m68k-elf-
make -C "$out" -f /home/claude/mk-nolto.gen -j8 release GDK=/home/claude/sgdkr OS=Linux PREFIX=$t CC=${t}gcc LD=${t}ld AR=${t}ar NM=${t}nm OBJCPY=${t}objcopy > "$out.build.log" 2>&1 || { grep -iE " error|undefined" "$out.build.log" | head; exit 1; }
echo "$out/out/release/rom.bin"
