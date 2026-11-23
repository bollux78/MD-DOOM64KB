#!/usr/bin/env bash
# Runner task 7: linker script data/bss symbols
out=${1:?out dir}
GDK="$HOME/Projetos/marsdev/sgdk/SGDK"
sed -n 1,125p "$GDK/md.ld"
