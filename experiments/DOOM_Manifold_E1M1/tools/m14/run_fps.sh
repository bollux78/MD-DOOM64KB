#!/bin/bash
# usage: run_fps.sh ROM.bin ELF SECONDS OUT.txt   (sem throttle; 60 VBlanks = 1 s emulado)
rom=$1; elf=$2; sec=$3; out=$4
a=$(/home/claude/mars/m68k-elf/bin/m68k-elf-nm "$elf" | awk '$3=="cur_frame"{print substr($1,3)}')
ADDR_CF=$a FPS_OUT=$out timeout 900 /usr/games/mame genesis -cart "$rom" -autoboot_script /home/claude/md-doom64kb/experiments/DOOM_Manifold_E1M1/tools/m14/fps.lua -video none -sound none -nothrottle -seconds_to_run $sec -skip_gameinfo >/dev/null 2>&1
awk 'NR==1{f0=$2;n0=$1} END{printf "FPS medio: %.2f (frames %d em %d s)\n",($2-f0)/(($1-n0)/60),$2-f0,($1-n0)/60}' "$out"
