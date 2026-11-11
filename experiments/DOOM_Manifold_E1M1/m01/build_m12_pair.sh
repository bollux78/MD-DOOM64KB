#!/usr/bin/env bash
set -euo pipefail
WAD="$HOME/Projetos/doom-md/assets/wads/doom1.wad"
python3 - "$WAD" <<'PY'
import sys,pathlib,hashlib
p=pathlib.Path(sys.argv[1])
assert p.is_file() and p.stat().st_size==4196020
assert hashlib.sha256(p.read_bytes()).hexdigest()=="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
PY
stage="$RUNNER_TEMP/manifold-m12-pair-$GITHUB_RUN_ID"
python3 experiments/DOOM_Manifold_E1M1/m01/bootstrap.py --out "$stage"
DOOM_R25_MUSIC=1 python3 scripts/lab/prepare_r25_music.py
test -s res/r25-e1m1.vgm
for variant in control objects; do
  if [ "$variant" = objects ]; then with_objects=1; else with_objects=0; fi
  MANIFOLD_OBJECTS="$with_objects" MANIFOLD_MUSIC=1 MANIFOLD_MUSIC_VGM="$GITHUB_WORKSPACE/res/r25-e1m1.vgm" \
  python3 experiments/DOOM_Manifold_E1M1/m01/stage_rom.py --source "$stage/manifold" --wad "$WAD" --out "$stage/$variant"
done
gdk=""
for d in "$GITHUB_WORKSPACE/vendor/sgdk" "$HOME/Projetos/doom-md/vendor/sgdk" "$HOME/Projetos/MD-DOOM64KB/vendor/sgdk" "$HOME/mars/sgdk" "$HOME/mars/SGDK" "$HOME/sgdk" /opt/sgdk; do
  if test -f "$d/makefile.gen"; then gdk="$d"; break; fi
done
if test -z "$gdk"; then
  while IFS= read -r sdkfile; do gdk="${sdkfile%/makefile.gen}"; break; done < <(find "$HOME" /opt -maxdepth 9 -type f -name makefile.gen 2>/dev/null | head -30)
fi
test -n "$gdk" || { echo 'SGDK missing'; exit 1; }
native_xgm="$HOME/mars/m68k-elf/bin/xgmtool"
if test ! -x "$gdk/bin/xgmtool"; then
  test -x "$native_xgm"
  test ! -e "$gdk/bin/xgmtool" && test ! -L "$gdk/bin/xgmtool"
  ln -s "$native_xgm" "$gdk/bin/xgmtool"
fi
export GDK="$gdk" PREFIX=m68k-elf-
export PATH="$HOME/mars/m68k-elf/bin:$HOME/toolchains/mars/m68k-elf/bin:$GDK/bin:$PATH"
tc="$HOME/mars/m68k-elf/bin/m68k-elf-"
test -x "${tc}gcc"
python3 - "$gdk/makefile.gen" "$stage/portable.gen" <<'PY'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text()
pat='-flto -flto=auto -ffat-lto-objects'
assert s.count(pat)>=2
pathlib.Path(sys.argv[2]).write_text(s.replace(pat,'-fno-lto'))
PY
mkdir -p "$RUNNER_TEMP/m12-pair"
for variant in control objects; do
  test -e "$stage/$variant/src/math3D.h" || ln -s math3d.h "$stage/$variant/src/math3D.h"
  make -C "$stage/$variant" -f "$stage/portable.gen" -j2 release \
    OS=Linux PREFIX="$tc" CC="${tc}gcc" LD="${tc}ld" AR="${tc}ar" \
    NM="${tc}nm" OBJCPY="${tc}objcopy"
  test -s "$stage/$variant/out/rom.bin"
  cp "$stage/$variant/out/rom.bin" "$RUNNER_TEMP/m12-pair/M12-${variant}-H32.bin"
done
(cd "$RUNNER_TEMP/m12-pair" && sha256sum M12-*.bin) > "$RUNNER_TEMP/m12-pair/SHA256SUMS.txt"
cat > "$RUNNER_TEMP/m12-pair/LEIA-ME.txt" <<'TXT'
M12-control-H32.bin: E1M1 M11 musical, sem objetos adicionados.
M12-objects-H32.bin: mesma base, com sprites e THINGS estaticas da E1M1.
Ambas: H32, HUD DOOM, musica XGM. Objetos ainda sao apenas visuais.
Testar as duas no mesmo percurso; ROMs experimentais, console nao validado.
TXT
echo 'M12: only 2 ROMs staged and built'
