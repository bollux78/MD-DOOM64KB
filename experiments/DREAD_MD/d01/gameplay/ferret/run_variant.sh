#!/usr/bin/env bash
set -euo pipefail
variant=${1:?};out=${2:?};core=${3:?}
root=$(cd "$(dirname "$0")/../.." && pwd)
wad=/home/dan/Projetos/doom-md/assets/wads/doom1.wad
export OPENBLAS_NUM_THREADS=1
mkdir -p "$out/release"
GDK=''
for d in "$HOME/Projetos/marsdev/sgdk/SGDK" "$HOME/Projetos/doom-md/vendor/sgdk" /opt/sgdk; do
 if [[ -f "$d/makefile.gen" ]]; then GDK=$d;break;fi
done
: "${GDK:?SGDK not found}"
export GDK DREAD_TC="$HOME/mars/m68k-elf/bin/m68k-elf-" PATH="$HOME/mars/m68k-elf/bin:$GDK/bin:$PATH"
case $variant in
 CONTROL)
  if [[ -s "$out/EPISODE.bin" && -s "$out/EPISODE.elf" ]] && [[ $(sha256sum "$out/EPISODE.bin" | cut -d' ' -f1) == bada47a0c028fb70f4f76ddbdd495ea1c0fd6b9797c101b54cb1b064ffc5ad56 ]]; then
    echo 'Reusing verified CONTROL ROM from run45607031274; repeating QA and NTSC benchmarks' | tee -a "$out/build.log"
  else
    (unset DREAD_FERRET_RENDERER DREAD_FERRET_COLUMN_RLE DREAD_SOURCE_PIXELS; bash "$root/gameplay/optimization/compile_one.sh" CONTROL "$out") > "$out/build.log" 2>&1
  fi ;;
 FERRET160|FERRET80)
  flags='';[[ $variant != FERRET80 ]] || flags='-DSTART_MODE=9'
  DREAD_FERRET_FLAGS="$flags" bash "$root/gameplay/ferret/build.sh" "$wad" "$out" > "$out/build.log" 2>&1
  cp "$out/EPISODE.bin" "$out/release/DREAD-C7-$variant.bin"
  cp "$out/EPISODE.elf" "$out/release/DREAD-C7-$variant.elf" ;;
 *) exit 2;;
esac
python3 - "$out" "$variant" "${DREAD_TC}nm" <<'PY'
from pathlib import Path
import sys,subprocess,json,hashlib
p=Path(sys.argv[1]);v=sys.argv[2];s={}
for line in subprocess.check_output([sys.argv[3],str(p/'EPISODE.elf')],text=True).splitlines():
 x=line.split()
 if len(x)==3:s[x[2]]=int(x[0],16)&65535
assert {'bench_req','bench_done','bench_frames','bench_vints'}<=s.keys()
(p/'symbols.json').write_text(json.dumps(s))
(p/'release'/'manifest.json').write_text(json.dumps({'variant':v,'bytes':(p/'EPISODE.bin').stat().st_size,'sha256':hashlib.sha256((p/'EPISODE.bin').read_bytes()).hexdigest()},indent=2))
PY
export DREAD_TEST_CORE="$core" DREAD_TEST_NM="${DREAD_TC}nm" DREAD_TEST_WAD="$wad"
export DREAD_TEST_ROOT="$out/qa" DREAD_GAME_VARIANT=game
export PYTHONPATH="$root/native-perspective:$root/gameplay:${PYTHONPATH:-}"
mkdir -p "$out/qa/game"
cp "$out/EPISODE.bin" "$out/EPISODE.elf" "$out/qa/game/"
if [[ $variant != CONTROL ]]; then
 python3 "$root/gameplay/ferret/qa_episode.py" > "$out/qa/episode.log" 2>&1
fi
for qa in qa_mechanisms.py qa_autoaim_grates.py qa_progression.py qa_combat_keys_end.py; do
 python3 "$root/gameplay/$qa" > "$out/qa/$qa.log" 2>&1
done
python3 "$root/gameplay/ferret/validate_qa.py" "$out/qa"
for mode in 1 2; do
 # Retry an emulator timeout/crash once; deterministic assertion failures are kept in logs.
 python3 "$root/gameplay/ferret/bench_mame.py" --rom "$out/EPISODE.bin" --symbols "$out/symbols.json" --mode "$mode" --result "$out/bench-mode$mode.json" || {
  cp "$out/mame-mode$mode.log" "$out/mame-mode$mode-attempt1.log" 2>/dev/null || true
  python3 "$root/gameplay/ferret/bench_mame.py" --rom "$out/EPISODE.bin" --symbols "$out/symbols.json" --mode "$mode" --result "$out/bench-mode$mode.json"
 }
done
