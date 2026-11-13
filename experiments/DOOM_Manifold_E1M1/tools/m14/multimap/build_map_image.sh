#!/bin/bash
# usage: build_map_image.sh E1M2  -> /tmp/m12/mm_E1M2/out/release/rom.bin (linked at 0x080000, split layout: common block + map block at 0x300000)
m=$1
D=$(dirname "$(readlink -f "$0")")
R=/home/claude/md-doom64kb
t=/home/claude/mars/m68k-elf/bin/m68k-elf-
name=mm_$m
extra=""
case $m in
  E1M1) extra="";;
  E1M4) extra="MANIFOLD_SKY_MERGE=0 MANIFOLD_MAX_CELL_WALLS=24";;
  E1M5) extra="MANIFOLD_MAX_CELL_WALLS=24";;
  E1M3) extra="MANIFOLD_MAX_WALLS=4096 MANIFOLD_MAX_CELL_WALLS=24";;
  E1M6) extra="MANIFOLD_SPLIT_PIECES=1 MANIFOLD_MAX_WALLS=4096 MANIFOLD_MAX_CELL_WALLS=24";;
  E1M7) extra="MANIFOLD_SPLIT_PIECES=1 MANIFOLD_MAX_WALLS=4096 MANIFOLD_MAX_CELL_WALLS=24";;
  E1M8) extra="MANIFOLD_MAX_WALLS=4096 MANIFOLD_MAX_CELL_WALLS=24";;
esac
doors="MANIFOLD_DOORS=0"
[ "$m" = "E1M1" ] && doors="MANIFOLD_DOORS=1"
F=$(cat /tmp/m14x/flags_walk.txt)
export MANIFOLD_MONSTERS=1 MANIFOLD_MONSTERS_INACTIVE=1 MANIFOLD_MUSIC=1 MANIFOLD_MUSIC_VGM=$R/res/r25-$(echo $m | tr A-Z a-z).vgm
out=/tmp/m12/$name; rm -rf "$out"
env $F $doors MANIFOLD_MAP=$m MANIFOLD_VDP_SAFE=2 MANIFOLD_SWEPT=1 MANIFOLD_GRATE_SPRITES=0 MANIFOLD_GRATES=0 MANIFOLD_FALL=1 MANIFOLD_FALL_FAST=1 \
  MANIFOLD_WEAPON_FIX=1 MANIFOLD_INPUT_FIX=1 MANIFOLD_UNPACK_MAP=1 MANIFOLD_VG_MICRO=1 MANIFOLD_SPLIT_LINES=0 MANIFOLD_OBJ_HEIGHT_PCT=${HPCT:-80} MANIFOLD_START_MENU=1 $extra \
  python3 $R/experiments/DOOM_Manifold_E1M1/m01/stage_rom.py --source /home/claude/manifold-up --wad /home/claude/wad/d.wad --out "$out" > "$out.stage.log" 2>&1 || { tail -5 "$out.stage.log"; exit 1; }
ln -sf math3d.h "$out/src/math3D.h"
make -C "$out" -f $D/mk-split.gen -j4 release GDK=/home/claude/sgdkr OS=Linux PREFIX=$t CC=${t}gcc LD=${t}ld AR=${t}ar NM=${t}nm OBJCPY=${t}objcopy > "$out.build.log" 2>&1 || { grep -iE " error|undefined" "$out.build.log" | head; exit 1; }
echo "OK $m $(stat -c %s $out/out/release/rom.bin) bytes entry=$(${t}nm $out/out/release/rom.out | awk '$3=="_Entry_Point"{print $1}')"
