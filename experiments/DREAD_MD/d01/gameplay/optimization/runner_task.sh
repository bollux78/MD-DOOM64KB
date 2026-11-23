#!/usr/bin/env bash
# Runner task 3: how does the SGDK boot code treat RAM on a hard reset? (to keep menu settings across SYS_hardReset)
out=${1:?out dir}
for d in "$HOME/Projetos/marsdev/sgdk/SGDK" "$HOME/Projetos/doom-md/vendor/sgdk" "$HOME/mars/m68k-elf" /opt/sgdk; do
  if [[ -f "$d/makefile.gen" ]]; then GDK="$d"; break; fi
done
echo "GDK=$GDK"
for f in "$GDK/src/boot/sega.s" "$(dirname "$0")/../../src/boot/sega.s"; do [[ -f "$f" ]] && { echo "== $f"; cat "$f" > "$out/sega.s"; grep -n -i "clear\|ram\|reset\|0xFFFF\|hard\|warm\|magic" "$f" | head -60; }; done
echo "== SYS_hardReset"
grep -rn "SYS_hardReset" -A12 "$GDK/src/sys.c" | head -50
ls "$(dirname "$0")/../../src/boot" 2>/dev/null
