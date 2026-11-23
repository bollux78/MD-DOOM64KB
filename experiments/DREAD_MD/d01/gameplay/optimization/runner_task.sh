#!/usr/bin/env bash
# Runner task 4: SGDK hard reset and RAM clearing details
out=${1:?out dir}
GDK="$HOME/Projetos/marsdev/sgdk/SGDK"
echo "== sega.s 55-100 and 285-330"; sed -n 55,100p "$GDK/src/boot/sega.s"; echo ...; sed -n 285,330p "$GDK/src/boot/sega.s"
echo "== grep hardReset / bss in GDK"; grep -rn "hardReset\|SYS_reset" "$GDK/src" "$GDK/inc" "$GDK/md.ld" 2>/dev/null | head -20
echo "== linker"; ls "$GDK"; grep -n "bss\|noinit\|NOLOAD" "$GDK/md.ld" 2>/dev/null | head -20
