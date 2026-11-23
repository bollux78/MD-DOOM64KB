#!/usr/bin/env bash
# Runner task 5: SGDK SYS_reset/SYS_hardReset and the crt0 RAM clear
out=${1:?out dir}
GDK="$HOME/Projetos/marsdev/sgdk/SGDK"
echo "== sys_a.s 1-60"; sed -n 1,60p "$GDK/src/sys_a.s"
echo "== _reset_entry / _start_entry"; grep -n "_reset_entry\|_start_entry\|_bstart\|_bend\|ClearBSS\|clear" "$GDK/src/boot/sega.s" "$GDK/src/boot/rom_head.c" "$GDK/src/crt0"* 2>/dev/null | head -20
ls "$GDK/src/boot"
