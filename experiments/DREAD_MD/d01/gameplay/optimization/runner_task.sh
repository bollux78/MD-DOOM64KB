#!/usr/bin/env bash
# Runner task: assemble colasm.s / segasm.s with the runner's m68k toolchain (syntax and size check only).
out=${1:?out dir}
root="$(cd "$(dirname "$0")/../.." && pwd)"
TC="$HOME/mars/m68k-elf/bin/m68k-elf-"
echo "toolchain: $(${TC}gcc --version | head -1)"
FL="-m68000 -x assembler-with-cpp -DDREAD_NATIVE_PERSPECTIVE -DDREAD_EPISODE -DDREAD_COMBAT -DDREAD_GAMEPLAY -DDREAD_COMBAT_12_20"
for f in colasm segasm; do
  echo "== $f.s"
  ${TC}gcc $FL -c "$root/src/$f.s" -o "$out/$f.o" && ${TC}size "$out/$f.o" && ${TC}objdump -d "$out/$f.o" > "$out/$f.dis" && echo "ok ($(wc -l < "$out/$f.dis") lines of disassembly)"
done
# task 2: assembler check of colasm.s with the wrap-splitting tex_native (also DREAD_NATIVE_PERSPECTIVE on and off)
# trigger
