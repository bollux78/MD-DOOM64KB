#!/bin/bash
# usage: buildwalk.sh E1M2 [extra env]
m=$1; shift
F=$(cat $(dirname $0)/flags_walk.txt)
cd /home/claude/md-doom64kb
bash experiments/DOOM_Manifold_E1M1/tools/m14/build_local.sh m14_$m $F MANIFOLD_MAP=$m MANIFOLD_VDP_SAFE=2 MANIFOLD_SWEPT=1 MANIFOLD_GRATE_SPRITES=0 MANIFOLD_GRATES=0 MANIFOLD_FALL=1 MANIFOLD_FALL_FAST=1 "MANIFOLD_ROM_NAME=M14 $m WALK" "MANIFOLD_ROM_TEST=$m WALK AROUND FAST FALL" "$@" 2>&1 | tail -4
grep -E "max walls per cell|decorations cut|THINGS inserted|SPAWN CELL" /tmp/m12/m14_$m.stage.log
