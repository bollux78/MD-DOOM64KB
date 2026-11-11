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
for variant in h32 h40; do
  if [ "$variant" = h40 ]; then width=0; else width=1; fi
  MANIFOLD_BSP=1 MANIFOLD_RADIUS=1 MANIFOLD_STABLE_VIEW=1 MANIFOLD_H32="$width" MANIFOLD_MUSIC=1 MANIFOLD_MUSIC_VGM="$GITHUB_WORKSPACE/res/r25-e1m1.vgm" \
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
for variant in h32 h40; do
  test -e "$stage/$variant/src/math3D.h" || ln -s math3d.h "$stage/$variant/src/math3D.h"
  make -C "$stage/$variant" -f "$stage/portable.gen" -j2 release \
    OS=Linux PREFIX="$tc" CC="${tc}gcc" LD="${tc}ld" AR="${tc}ar" \
    NM="${tc}nm" OBJCPY="${tc}objcopy"
  test -s "$stage/$variant/out/rom.bin"
  if [ "$variant" = doors ]; then
    ELF="$stage/$variant/out/release/rom.out"
    test -s "$ELF" || ELF="$stage/$variant/out/rom.out"
    if test -s "$ELF"; then
      echo '=== M12 diagnostics: A-button address error (PC 00E5EC, hint 007F3E) ==='
      "${tc}addr2line" -f -e "$ELF" 0xE5EC 0x7F3E || true
      "${tc}nm" -n "$ELF" | python3 -c 'import sys; wanted=(0xE5EC,0x7F3E); rows=[]; [(rows.append((int(p[0],16),p[-1]))) for l in sys.stdin if (p:=l.split()) and len(p)>=3 and all(c in "0123456789abcdefABCDEF" for c in p[0])]; print("\\n".join("address 0x%X nearest symbol %s @ 0x%X"%(a, *(lambda q:(q[1],q[0]))(max((r for r in rows if r[0]<=a),default=(0,"none")))) for a in wanted))' || true
    fi
  fi
  cp "$stage/$variant/out/rom.bin" "$RUNNER_TEMP/m12-claudio/m12stable-${variant}.bin"
done
(cd "$RUNNER_TEMP/m12-claudio" && sha256sum m12stable-*.bin) > "$RUNNER_TEMP/m12-claudio/SHA256SUMS.txt"
cat > "$RUNNER_TEMP/m12-claudio/LEIA-ME.txt" <<'TXT'
M12-pickups-control-H32.bin: M12 com coleta APROVADA; portas permanentemente abertas.
M12-doors-H32.bin: mesma M12 com quatro setores de porta inicialmente fechados.
Ambas: H32, HUD DOOM, musica XGM, objetos e itens coletaveis.
M12-doors: botao B perto da porta; teto sobe gradualmente, atravesse, fecha apos 105 ticks (~3 s a 35 Hz).
M12-doors: A NAO inicia animacao de recarga nesta versao DIAGNOSTICA; testar se o crash desapareceu.
Setores E1M1 em teste: 4, 68, 76, 81. Sem tranca/chave, sem triggers do WAD ainda.
Verifique colisao, visual, FPS e se porta NAO fecha enquanto jogador estiver dentro.
Nao promover experimental sem aprovacao no console.
TXT
echo 'M12 Claudio: two renderer ROMs staged and built'
