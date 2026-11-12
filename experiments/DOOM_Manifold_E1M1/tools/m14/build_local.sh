#!/bin/bash
# Local replica of the workflow's M12 variants (no runner, no release). usage: m12build.sh NAME [env...]
set -e
name=$1; shift
R=/home/claude/md-doom64kb
W=/tmp/m12
out=$W/$name
rm -rf "$out"; mkdir -p "$W"
export MANIFOLD_MUSIC=1 MANIFOLD_MUSIC_VGM=$R/res/r25-e1m1.vgm
env "$@" python3 $R/experiments/DOOM_Manifold_E1M1/m01/stage_rom.py \
  --source /home/claude/manifold-up --wad /home/claude/wad/d.wad --out "$out" > "$out.stage.log" 2>&1 || { tail -5 "$out.stage.log"; exit 1; }
ln -sf math3d.h "$out/src/math3D.h"
t=/home/claude/mars/m68k-elf/bin/m68k-elf-
make -C "$out" -f /home/claude/mk-nolto.gen -j4 release GDK=/home/claude/sgdkr OS=Linux PREFIX=$t CC=${t}gcc LD=${t}ld AR=${t}ar NM=${t}nm OBJCPY=${t}objcopy > "$out.build.log" 2>&1 || { grep -iE " error|undefined" "$out.build.log" | head; exit 1; }
echo "OK $name $out/out/release/rom.bin"
