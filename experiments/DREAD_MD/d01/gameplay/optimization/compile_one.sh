#!/usr/bin/env bash
# Dedicated self-hosted experimental C7 build; no modifications to C7 stable.
set -euo pipefail
variant=${1:?variant required}
output=${2:?output required}
root="$(cd "$(dirname "$0")/../.." && pwd)"
test -s /home/dan/Projetos/doom-md/assets/wads/doom1.wad
wad=/home/dan/Projetos/doom-md/assets/wads/doom1.wad
test -x "$HOME/mars/m68k-elf/bin/m68k-elf-gcc"
GDK=""
for d in "$HOME/Projetos/marsdev/sgdk/SGDK" "$HOME/Projetos/doom-md/vendor/sgdk" "$HOME/mars/m68k-elf" /opt/sgdk; do
  if [[ -f "$d/makefile.gen" ]]; then GDK="$d"; break; fi
done
test -n "$GDK"
export GDK PATH="$HOME/mars/m68k-elf/bin:$GDK/bin:$PATH"
export DREAD_TC="$HOME/mars/m68k-elf/bin/m68k-elf-"
export OPENBLAS_NUM_THREADS=1 DREAD_WEAPON_DITHER=1 DREAD_GRATE_HALF_RES=1
unset DREAD_SSF DREAD_COPY_SEGA_S DREAD_PREPARED_MAPS
mkdir -p "$output/release"
python3 -m py_compile "$root/tools/conv.py" "$root/tools/map_reduce.py"
bash "$root/gameplay/optimization/variant.sh" "$variant" "$wad" "$output"
test -s "$output/EPISODE.bin"
test -s "$output/EPISODE.elf"
bytes=$(stat -c %s "$output/EPISODE.bin")
(( bytes <= 4194304 ))
cp "$output/EPISODE.bin" "$output/release/DREAD-C7-OPT-$variant.bin"
# Publish the ELF only for the shareware WAD (doom1.wad): it carries the same data as the public ROM and lets the
# profiler map PC samples to functions. Any other WAD (registered/full game) keeps the ELF private on the runner.
case "$(basename "$wad" | tr '[:upper:]' '[:lower:]')" in
  doom1.wad) cp "$output/EPISODE.elf" "$output/release/DREAD-C7-OPT-$variant.elf" ;;
  *) echo "ELF kept private: WAD is not the shareware doom1.wad" ;;
esac
mkdir -p "$output/release/geometry/$variant"
cp "$output"/geometry/E1M*.json "$output/release/geometry/$variant/"
sha256sum "$output/release/DREAD-C7-OPT-$variant.bin" > "$output/release/SHA256-$variant.txt"
if [[ $variant == GEO_SAFE ]]; then
  # host-side proof that the reduced geometry still draws the same image (no ROM or emulator needed)
  bash "$root/gameplay/optimization/verify_geo_exact.sh" "$wad" "E1M1 E1M2 E1M5 E1M8" 1500 "$output/geo-verify" "control merge" \
    | tee "$output/release/geo-verify-GEO_SAFE.txt" || echo "::warning::GEO_SAFE host verification FAILED (see geo-verify-GEO_SAFE.txt)"
  cp "$output/geo-verify/summary.json" "$output/release/geo-verify-GEO_SAFE.json" 2>/dev/null || true
fi
python3 - "$output" "$variant" <<'PY'
from pathlib import Path
import subprocess,json,hashlib,sys
out=Path(sys.argv[1]);v=sys.argv[2]
elf=out/'EPISODE.elf';rom=out/'EPISODE.bin'
raw=subprocess.check_output([str(Path.home()/'mars/m68k-elf/bin/m68k-elf-nm'),str(elf)],text=True)
wanted={'bench_req','bench_done','bench_frames','bench_vints','selected_map','vints'}
syms={}
for line in raw.splitlines():
    p=line.split()
    if len(p)>=3 and p[-1] in wanted:
        syms[p[-1]]=int(p[0],16)&65535
assert wanted.issubset(syms),wanted-set(syms)
(out/'release'/f'symbols-{v}.json').write_text(json.dumps(syms,indent=2)+'\n')
(out/'release'/f'manifest-{v}.json').write_text(json.dumps({
    'variant':v,'rom_bytes':rom.stat().st_size,
    'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),
    'benchmark':'pending MAME','base_c7':'c816e6c72a8fc6a3bc989b347ea7166fda835893'},indent=2)+'\n')
print(f'BUILD {v} OK: {rom.stat().st_size} bytes',flush=True)
PY
