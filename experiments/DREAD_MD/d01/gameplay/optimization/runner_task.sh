#!/usr/bin/env bash
# Runner task 6: where _start_entry/_reset_entry are defined and what they clear
out=${1:?out dir}
GDK="$HOME/Projetos/marsdev/sgdk/SGDK"
f=$(grep -rln "^_reset_entry\|_reset_entry:" "$GDK/src" 2>/dev/null | head -3); echo "files: $f"
for x in $f; do echo "== $x"; grep -n "_start_entry\|_reset_entry\|bss\|clear\|0xFFFF0000\|0xE0FF0000\|dbra\|rept\|_bend\|_bstart" "$x" | head -40; done
