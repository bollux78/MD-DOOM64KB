#!/usr/bin/env bash
set -euo pipefail
WAD="$HOME/Projetos/doom-md/assets/wads/doom1.wad"
python3 - "$WAD" <<'PY'
import sys,pathlib,hashlib
p=pathlib.Path(sys.argv[1])
assert p.is_file() and p.stat().st_size==4196020
assert hashlib.sha256(p.read_bytes()).hexdigest()=="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
PY
stage="$RUNNER_TEMP/manifold-m12-claudio-$GITHUB_RUN_ID"
python3 experiments/DOOM_Manifold_E1M1/m01/bootstrap.py --out "$stage"
DOOM_R25_MUSIC=1 python3 scripts/lab/prepare_r25_music.py
test -s res/r25-e1m1.vgm
for variant in h40-control h40-fixed; do
  if [ "$variant" = h40-fixed ]; then bsp_fix=1; doom_blocking=1; else bsp_fix=0; doom_blocking=0; fi
  MANIFOLD_BSP=1 MANIFOLD_RADIUS=1 MANIFOLD_STABLE_VIEW=1 MANIFOLD_H32=0 MANIFOLD_BSP_PRECISION="$bsp_fix" MANIFOLD_DOOM_BLOCKING="$doom_blocking" MANIFOLD_MUSIC=1 MANIFOLD_MUSIC_VGM="$GITHUB_WORKSPACE/res/r25-e1m1.vgm" \
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
mkdir -p "$RUNNER_TEMP/m12-claudio"
for variant in h40-control h40-fixed; do
  test -e "$stage/$variant/src/math3D.h" || ln -s math3d.h "$stage/$variant/src/math3D.h"
  make -C "$stage/$variant" -f "$stage/portable.gen" -j2 release \
    OS=Linux PREFIX="$tc" CC="${tc}gcc" LD="${tc}ld" AR="${tc}ar" \
    NM="${tc}nm" OBJCPY="${tc}objcopy"
  test -s "$stage/$variant/out/rom.bin"
  cp "$stage/$variant/out/rom.bin" "$RUNNER_TEMP/m12-claudio/m12-${variant}.bin"
done
(cd "$RUNNER_TEMP/m12-claudio" && sha256sum m12-*.bin) > "$RUNNER_TEMP/m12-claudio/SHA256SUMS.txt"
cat > "$RUNNER_TEMP/m12-claudio/LEIA-ME.txt" <<'TXT'
M12 H40 control vs corrected. Both: BSP renderer, stable view,
radius 16, music, Doom HUD, same E1M1, no items or doors.
m12-h40-control.bin: original Claudio H40, as previously tested in BlastEm.
m12-h40-fixed.bin: signed 32-bit BSP frustum coefficients (scaled)
and collision honoring DOOM LINEDEF BLOCKING flag for windows.
TEST: outside intermittent missing walls/triangles, passage through
spawn room window, and FPS. No physical hardware validation yet.
TXT
echo 'M12 H40: two strictly comparable ROMs staged and built'
